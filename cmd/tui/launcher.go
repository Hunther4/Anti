package main

import (
	crypto_rand "crypto/rand"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"sync"
	"syscall"
	"time"

	"github.com/charmbracelet/bubbles/textinput"
	"github.com/charmbracelet/bubbles/viewport"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

// Screen types
type Screen int

const (
	ScreenMain Screen = iota
	ScreenKeys
	ScreenModel
	ScreenSetup
	ScreenAPIInput
	ScreenChat
)

// Colors & Design tokens
var (
	cyan    = lipgloss.Color("#00f0ff")
	magenta = lipgloss.Color("#ff003c")
	white   = lipgloss.Color("#f8fafc")
	gray    = lipgloss.Color("#94a3b8")
	darkGray = lipgloss.Color("#4b5563")
	purple  = lipgloss.Color("#5f5f87")
	yellow  = lipgloss.Color("#ffcc00")

	titleStyle = lipgloss.NewStyle().
			Foreground(cyan).
			Bold(true).
			MarginLeft(2).
			MarginBottom(1)

	subtitleStyle = lipgloss.NewStyle().
			Foreground(magenta).
			Italic(true).
			MarginLeft(2).
			MarginBottom(1)

	selectedItemStyle = lipgloss.NewStyle().
				Foreground(cyan).
				Bold(true)

	normalItemStyle = lipgloss.NewStyle().
			Foreground(white)

	sidebarStyle = lipgloss.NewStyle().
			Border(lipgloss.RoundedBorder()).
			BorderForeground(purple).
			Padding(1, 2).
			Width(40)

	mainContentStyle = lipgloss.NewStyle().
				Border(lipgloss.RoundedBorder()).
				BorderForeground(cyan).
				Padding(1, 2).
				Width(44)
)

// Config representation
type Config struct {
	AgentName              string `json:"agent_name"`
	Language               string `json:"language"`
	Personality            string `json:"personality"`
	Provider               string `json:"provider"`
	Model                  string `json:"model"`
	LMStudioURL            string `json:"lm_studio_url"`
	OllamaURL              string `json:"ollama_url"`
	OpenAIAPIKey           string `json:"openai_api_key,omitempty"`
	DeepSeekAPIKey         string `json:"deepseek_api_key,omitempty"`
	GeminiAPIKey           string `json:"gemini_api_key,omitempty"`
	AnthropicAPIKey        string `json:"anthropic_api_key,omitempty"`
	MinimaxAPIKey          string `json:"minimax_api_key,omitempty"`
	OpenAICompatibleAPIKey string `json:"openaicompatible_api_key,omitempty"`
	OpenAICompatibleURL    string `json:"openaicompatible_url,omitempty"`
	MaxIterations          int    `json:"max_iterations"`
	ReportFormat           string `json:"report_format"`
}

type ModelStatus struct {
	LMStudioOnline   bool
	OllamaOnline     bool
	WorkspaceFiles   int
	EngramsCount     int
	SandboxOnline    bool
	SandboxMemUsedMB int64
	SandboxMemLimMB  int64
	BootEngrams      int
}

type model struct {
	cursor          int
	choices         []string
	config          Config
	status          ModelStatus
	screen          Screen
	selectedAPI     string
	apiInput        textinput.Model
	chatInput       textinput.Model
	chatHistory     []string
	activeJobId     string
	chatViewport    viewport.Model
	viewingResponse bool
	width           int
	height          int
	err             error
	quitting        bool
	pythonPath      string
	lastStatusCheck time.Time
}

type processFinishedMsg struct{}
type sandboxResetMsg struct {
	err error
}
type sandboxStatsMsg struct {
	usedMB int64
	limMB  int64
	online bool
}

type statusData struct {
	LMStudioOnline  bool
	OllamaOnline    bool
	WorkspaceFiles  int
	EngramsCount    int
	BootEngrams     int
	SandboxOnline   bool
}

type statusUpdateMsg struct {
	data statusData
}

func tickSandboxStats() tea.Cmd {
	return tea.Tick(5*time.Second, func(_ time.Time) tea.Msg {
		used, lim, ok := GetSandboxMemoryMB()
		return sandboxStatsMsg{usedMB: used, limMB: lim, online: ok}
	})
}

func (m *model) sendChatMessage(msg string) tea.Cmd {
	return func() tea.Msg {
		url := "http://localhost:8000/api/chat"
		payload := map[string]string{"message": msg}
		body, _ := json.Marshal(payload)

		resp, err := SignedPost(url, "application/json", body)
		if err != nil {
			return chatErrorMsg{err: err}
		}
		defer resp.Body.Close()

		if resp.StatusCode == http.StatusForbidden {
			return chatErrorMsg{err: fmt.Errorf("403 forbidden: backend rejected HMAC signature")}
		}

		var res map[string]string
		if err := json.NewDecoder(resp.Body).Decode(&res); err != nil {
			return chatErrorMsg{err: err}
		}
		jobId := res["job_id"]
		if jobId == "" {
			return chatErrorMsg{err: fmt.Errorf("no job_id in response")}
		}
		return chatJobIdMsg{jobId: jobId}
	}
}

func (m *model) pollJobStatus(jobId string) tea.Cmd {
	return func() tea.Msg {
		url := fmt.Sprintf("http://localhost:8000/api/job/%s", jobId)
		resp, err := http.Get(url)
		if err != nil {
			return chatErrorMsg{err: err}
		}
		defer resp.Body.Close()

		var res map[string]interface{}
		if err := json.NewDecoder(resp.Body).Decode(&res); err != nil {
			return chatErrorMsg{err: err}
		}

		status, ok := res["status"].(string)
		if !ok {
			return chatErrorMsg{err: fmt.Errorf("invalid status type")}
		}

		if status == "completed" {
			result, ok := res["result"].(map[string]interface{})
			if !ok {
				return chatErrorMsg{err: fmt.Errorf("invalid result type")}
			}
			resp, ok := result["response"].(string)
			if !ok {
				resp = "No response from backend"
			}
			return chatResponseMsg{response: resp}
		} else if status == "failed" {
			return chatErrorMsg{err: fmt.Errorf("job failed: %v", res["error"])}
		}

		return pollContinueMsg{}
	}
}

type chatJobIdMsg struct{ jobId string }
type chatResponseMsg struct{ response string }
type chatErrorMsg struct{ err error }
type pollContinueMsg struct{}

func doResetSandbox(cwd string) tea.Cmd {
	return func() tea.Msg {
		err := ResetSandbox(cwd)
		return sandboxResetMsg{err: err}
	}
}

func initialModel() model {
	ti := textinput.New()
	ti.Placeholder = "Ingresá tu clave aquí..."
	ti.Focus()
	ti.CharLimit = 150
	ti.Width = 35

	cti := textinput.New()
	cti.Placeholder = "Escribí tu mensaje..."
	cti.Focus()
	cti.CharLimit = 500
	cti.Width = 40

	vp := viewport.New(40, 20)
	vp.SetContent("")

	pythonPath := "./venv/bin/python"
	if _, err := os.Stat(pythonPath); os.IsNotExist(err) {
		pythonPath = "python3"
	}

	m := model{
		choices: []string{
			"🖥️  Terminal (Ejecutar Anti)",
			"🌐  Web Host (Servidor Interactivo)",
			"💬  Chat (Hablar con Anti)",
			"🔌  Conexiones API (Gestionar Claves)",
			"🤖  Elegir Modelo (Seleccionar IA)",
			"⚙️  Instalación & Setup (Diagnóstico)",
			"🐳  Reiniciar Sandbox (Docker)",
			"🚪  Salir",
		},
		screen:       ScreenMain,
		apiInput:     ti,
		chatInput:    cti,
		chatViewport: vp,
		pythonPath:   pythonPath,
	}

	m.loadConfig()
	return m
}

// resolveConfigPath implements the "Local-First" strategy:
//   1. Prefer config.local.json (gitignored, may contain API keys).
//   2. Fallback to config.json (gitignored, team-shared defaults).
//   3. If neither exists, return an empty string and let the caller surface
//      the actionable error.
func resolveConfigPath() string {
	if _, err := os.Stat("config.local.json"); err == nil {
		return "config.local.json"
	}
	if _, err := os.Stat("config.json"); err == nil {
		return "config.json"
	}
	return ""
}

const configNotFoundMsg = "Configuration file not found. Please copy config.json.example to config.local.json and fill in your keys."

func (m *model) loadConfig() {
	configPath := resolveConfigPath()
	if configPath == "" {
		m.err = errors.New(configNotFoundMsg)
		m.config = Config{
			AgentName:   "Anti",
			Language:    "es",
			Provider:    "auto",
			LMStudioURL: "http://127.0.0.1:1234/v1",
			OllamaURL:   "http://127.0.0.1:11434",
		}
		return
	}

	file, err := os.ReadFile(configPath)
	if err != nil {
		m.err = err
		return
	}

	var cfg Config
	if err := json.Unmarshal(file, &cfg); err != nil {
		m.err = err
		return
	}
	m.config = cfg
}

func (m *model) saveConfig() {
	// Always write to the personal/local file so we never clobber shared
	// defaults. Create it from the example if nothing exists yet.
	configPath := "config.local.json"
	if _, err := os.Stat(configPath); os.IsNotExist(err) {
		if _, err := os.Stat("config.json"); err == nil {
			// Seed from defaults so the user inherits team-shared values.
			data, readErr := os.ReadFile("config.json")
			if readErr == nil {
				_ = os.WriteFile(configPath, data, 0600)
			}
		}
	}
	data, err := json.MarshalIndent(m.config, "", "  ")
	if err != nil {
		m.err = err
		return
	}
	_ = os.WriteFile(configPath, data, 0600)
}

func (m *model) asyncCheckStatus() tea.Cmd {
	if time.Since(m.lastStatusCheck) < 2*time.Second {
		return nil
	}
	m.lastStatusCheck = time.Now()
	return checkStatusAsync(m.config.LMStudioURL, m.config.OllamaURL)
}

func checkStatusAsync(lmStudioURL, ollamaURL string) tea.Cmd {
	return func() tea.Msg {
		var lmOnline, ollamaOnline, sandboxOnline bool
		var workspaceFiles, engramsCount, bootEngrams int
		var wg sync.WaitGroup

		files, _ := filepath.Glob("workspace/*")
		workspaceFiles = len(files)

		dbPath := "memory/cold_archive.db"
		if fi, err := os.Stat(dbPath); err == nil {
			engramsCount = int(fi.Size() / 1024)
		}

		if data, err := os.ReadFile("memory/boot_payload.json"); err == nil {
			var bp struct {
				BootEngramsCount int `json:"boot_engrams_count"`
			}
			if json.Unmarshal(data, &bp) == nil {
				bootEngrams = bp.BootEngramsCount
			}
		}

		wg.Add(3)

		go func() {
			defer wg.Done()
			client := http.Client{Timeout: 750 * time.Millisecond}
			url := lmStudioURL
			if url == "" {
				url = "http://127.0.0.1:1234/v1"
			}
			resp, err := client.Get(url + "/models")
			if err == nil && resp != nil {
				lmOnline = resp.StatusCode == 200
				_ = resp.Body.Close()
			}
		}()

		go func() {
			defer wg.Done()
			client := http.Client{Timeout: 750 * time.Millisecond}
			url := ollamaURL
			if url == "" {
				url = "http://127.0.0.1:11434"
			}
			resp, err := client.Get(url + "/api/tags")
			if err == nil && resp != nil {
				ollamaOnline = resp.StatusCode == 200
				_ = resp.Body.Close()
			}
		}()

		go func() {
			defer wg.Done()
			out, err := exec.Command("docker", "inspect", "-f", "{{.State.Running}}", "anti-sandbox").Output()
			if err == nil {
				sandboxOnline = strings.TrimSpace(string(out)) == "true"
			}
		}()

		wg.Wait()

		return statusUpdateMsg{data: statusData{
			LMStudioOnline: lmOnline,
			OllamaOnline:   ollamaOnline,
			WorkspaceFiles: workspaceFiles,
			EngramsCount:   engramsCount,
			BootEngrams:    bootEngrams,
			SandboxOnline:  sandboxOnline,
		}}
	}
}

func (m model) Init() tea.Cmd {
	return tea.Batch(
		textinput.Blink,
		tickSandboxStats(),
		m.asyncCheckStatus(),
	)
}

func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	var cmd tea.Cmd

	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.width = msg.Width
		m.height = msg.Height
		headerReserve := 10
		vpWidth := 40
		if m.width > 0 {
			if w := m.width/2 - 6; w > vpWidth {
				vpWidth = w
			}
		}
		vpHeight := m.height - headerReserve
		if vpHeight < 5 {
			vpHeight = 5
		}
		m.chatViewport.Width = vpWidth
		m.chatViewport.Height = vpHeight
		m.refreshChatViewport()
		return m, nil
	case sandboxStatsMsg:
		m.status.SandboxOnline = msg.online
		m.status.SandboxMemUsedMB = msg.usedMB
		m.status.SandboxMemLimMB = msg.limMB
		return m, tickSandboxStats()
	case statusUpdateMsg:
		m.status.LMStudioOnline = msg.data.LMStudioOnline
		m.status.OllamaOnline = msg.data.OllamaOnline
		m.status.WorkspaceFiles = msg.data.WorkspaceFiles
		m.status.EngramsCount = msg.data.EngramsCount
		m.status.BootEngrams = msg.data.BootEngrams
		m.status.SandboxOnline = msg.data.SandboxOnline
		return m, nil
	case chatJobIdMsg:
		m.activeJobId = msg.jobId
		m.refreshChatViewport()
		return m, m.pollJobStatus(msg.jobId)
	case chatResponseMsg:
		m.chatHistory = append(m.chatHistory, "Anti: "+msg.response)
		m.activeJobId = ""
		m.viewingResponse = true
		m.chatInput.Blur()
		m.refreshChatViewport()
		return m, nil
	case chatErrorMsg:
		m.chatHistory = append(m.chatHistory, "Error: "+msg.err.Error())
		m.activeJobId = ""
		m.viewingResponse = true
		m.chatInput.Blur()
		m.refreshChatViewport()
		return m, nil
	case pollContinueMsg:
		if m.activeJobId != "" {
			return m, m.pollJobStatus(m.activeJobId)
		}
		return m, nil
	case sandboxResetMsg:
		cmd = m.asyncCheckStatus()
		if msg.err != nil {
			m.err = msg.err
		} else {
			m.err = nil
		}
		return m, cmd
	case processFinishedMsg:
		return m, m.asyncCheckStatus()
	case tea.MouseMsg:
		if m.screen == ScreenChat && m.viewingResponse {
			var vpCmd tea.Cmd
			m.chatViewport, vpCmd = m.chatViewport.Update(msg)
			return m, vpCmd
		}
		return m, nil
	case tea.KeyMsg:
		switch msg.Type {
		case tea.KeyCtrlC, tea.KeyEsc:
			if m.screen != ScreenMain {
				m.screen = ScreenMain
				m.apiInput.Reset()
				m.chatInput.Reset()
				m.viewingResponse = false
				return m, m.asyncCheckStatus()
			}
			m.quitting = true
			return m, tea.Quit
		}

		if m.screen == ScreenMain {
			switch msg.String() {
			case "up", "k":
				if m.cursor > 0 {
					m.cursor--
				} else {
					m.cursor = len(m.choices) - 1
				}
			case "down", "j":
				if m.cursor < len(m.choices)-1 {
					m.cursor++
				} else {
					m.cursor = 0
				}
			case "enter":
				return m.handleMainMenuSelection()
			case "r":
				cwd, _ := os.Getwd()
				_ = ResetSandbox(cwd)
				cmd = m.asyncCheckStatus()
			case "p":
				_ = os.Remove("memory/logs.jsonl")
			}
		} else if m.screen == ScreenChat {
			if m.viewingResponse {
				switch msg.String() {
				case "enter":
					m.viewingResponse = false
					m.chatInput.Focus()
					return m, nil
				}
				var vpCmd tea.Cmd
				m.chatViewport, vpCmd = m.chatViewport.Update(msg)
				return m, vpCmd
			}
			switch msg.Type {
			case tea.KeyEnter:
				input := m.chatInput.Value()
				if input == "" {
					return m, nil
				}
				m.chatHistory = append(m.chatHistory, "User: "+input)
				m.chatInput.SetValue("")
				m.activeJobId = ""
				m.viewingResponse = false
				m.refreshChatViewport()
				return m, m.sendChatMessage(input)
			}
			var cmd2 tea.Cmd
			m.chatInput, cmd2 = m.chatInput.Update(msg)
			return m, cmd2
		} else if m.screen == ScreenKeys {
			switch msg.String() {
			case "1":
				m.selectedAPI = "openai"
				m.apiInput.SetValue(m.config.OpenAIAPIKey)
				m.screen = ScreenAPIInput
			case "2":
				m.selectedAPI = "deepseek"
				m.apiInput.SetValue(m.config.DeepSeekAPIKey)
				m.screen = ScreenAPIInput
			case "3":
				m.selectedAPI = "gemini"
				m.apiInput.SetValue(m.config.GeminiAPIKey)
				m.screen = ScreenAPIInput
			case "4":
				m.selectedAPI = "anthropic"
				m.apiInput.SetValue(m.config.AnthropicAPIKey)
				m.screen = ScreenAPIInput
			case "5":
				m.selectedAPI = "minimax"
				m.apiInput.SetValue(m.config.MinimaxAPIKey)
				m.screen = ScreenAPIInput
			case "6":
				m.selectedAPI = "openaicompatible"
				m.apiInput.SetValue(m.config.OpenAICompatibleAPIKey)
				m.screen = ScreenAPIInput
			case "0", "b", "esc":
				m.screen = ScreenMain
				cmd = m.asyncCheckStatus()
			}
		} else if m.screen == ScreenModel {
			switch msg.String() {
			case "1":
				m.config.Provider = "auto"
				m.saveConfig()
				m.screen = ScreenMain
			case "2":
				m.config.Provider = "lmstudio"
				m.config.Model = "Auto-detectado por LM Studio"
				m.saveConfig()
				m.screen = ScreenMain
			case "3":
				m.config.Provider = "ollama"
				m.config.Model = "Auto-detectado por Ollama"
				m.saveConfig()
				m.screen = ScreenMain
			case "4":
				m.config.Provider = "openai"
				m.config.Model = "gpt-4o"
				m.saveConfig()
				m.screen = ScreenMain
			case "5":
				m.config.Provider = "gemini"
				m.config.Model = "gemini-2.5-flash"
				m.saveConfig()
				m.screen = ScreenMain
			case "6":
				m.config.Provider = "deepseek"
				m.config.Model = "deepseek-chat"
				m.saveConfig()
				m.screen = ScreenMain
			case "7":
				m.config.Provider = "anthropic"
				m.config.Model = "claude-3-5-sonnet-20241022"
				m.saveConfig()
				m.screen = ScreenMain
			case "8":
				m.config.Provider = "minimax"
				m.config.Model = "abab6.5g-chat"
				m.saveConfig()
				m.screen = ScreenMain
			case "9":
				m.config.Provider = "openaicompatible"
				m.config.Model = "custom-model"
				m.saveConfig()
				m.screen = ScreenMain
			case "0", "esc":
				m.screen = ScreenMain
			}
		if m.screen == ScreenMain {
			cmd = m.asyncCheckStatus()
		}
		} else if m.screen == ScreenAPIInput {
			switch msg.Type {
			case tea.KeyEnter:
				val := m.apiInput.Value()
				switch m.selectedAPI {
				case "openai":
					m.config.OpenAIAPIKey = val
				case "deepseek":
					m.config.DeepSeekAPIKey = val
				case "gemini":
					m.config.GeminiAPIKey = val
				case "anthropic":
					m.config.AnthropicAPIKey = val
				case "minimax":
					m.config.MinimaxAPIKey = val
				case "openaicompatible":
					m.config.OpenAICompatibleAPIKey = val
				}
				m.saveConfig()
				m.screen = ScreenKeys
				m.apiInput.Reset()
				cmd = m.asyncCheckStatus()
			}
			m.apiInput, cmd = m.apiInput.Update(msg)
			return m, cmd
		} else if m.screen == ScreenSetup {
			switch msg.String() {
		case "enter", "esc", "b", "0":
			m.screen = ScreenMain
			cmd = m.asyncCheckStatus()
			}
		}
	}

	return m, cmd
}

func (m model) handleMainMenuSelection() (tea.Model, tea.Cmd) {
	switch m.cursor {
	case 0: // Terminal Client
		return m, tea.ExecProcess(exec.Command(m.pythonPath, "main.py"), func(err error) tea.Msg {
			return processFinishedMsg{}
		})
	case 1: // Web Host
		if err := startManagedServer(m.pythonPath); err != nil {
			m.err = err
		}
	case 2: // Chat
		m.screen = ScreenChat
		m.refreshChatViewport()
	case 3: // API Keys Management
		m.screen = ScreenKeys
	case 4: // Model / Provider Selection
		m.screen = ScreenModel
	case 5: // Setup / Diagnostics
		m.screen = ScreenSetup
	case 6: // Docker Sandbox Reset
		cwd, _ := os.Getwd()
		return m, doResetSandbox(cwd)
	case 7: // Exit
		m.quitting = true
		return m, tea.Quit
	}
	return m, nil
}

func (m *model) refreshChatViewport() {
	m.chatViewport.SetContent(m.buildChatContent())
	m.chatViewport.GotoBottom()
}

func (m model) buildChatContent() string {
	var chatArea strings.Builder
	userStyle := lipgloss.NewStyle().Foreground(cyan).Bold(true)
	antiStyle := lipgloss.NewStyle().Foreground(magenta).Bold(true)
	errorStyle := lipgloss.NewStyle().Foreground(gray).Italic(true)

	for _, msg := range m.chatHistory {
		switch {
		case strings.HasPrefix(msg, "User: "):
			chatArea.WriteString(userStyle.Render("User:") + " " + msg[6:] + "\n\n")
		case strings.HasPrefix(msg, "Anti: "):
			chatArea.WriteString(antiStyle.Render("Anti:") + " " + msg[6:] + "\n\n")
		default:
			chatArea.WriteString(errorStyle.Render(msg) + "\n\n")
		}
	}
	if m.activeJobId != "" {
		chatArea.WriteString(lipgloss.NewStyle().Foreground(yellow).Render("Anti is thinking... 💭") + "\n")
	}
	return chatArea.String()
}

// managedServerStdin holds the write end of the pipe feeding the managed
// Python server's stdin. The server's umbilical_cord thread monitors this
// fd; if we ever close it, the server emergency-shuts down. We intentionally
// do NOT close it for the lifetime of the TUI.
var managedServerStdin *os.File

// startManagedServer spawns the Python backend in ANTI_MANAGED=1 mode,
// generates a fresh 32-byte HMAC secret, writes it to the server's stdin,
// and stores it in the sharedSecret package var so SignedPost can sign
// subsequent requests. The process runs in the background and dies with
// the TUI (Pdeathsig).
func startManagedServer(pythonPath string) error {
	secret := make([]byte, 32)
	if _, err := crypto_rand.Read(secret); err != nil {
		return fmt.Errorf("generate secret: %w", err)
	}
	SetSharedSecret(secret)

	// If a previous managed server is still running, sever its stdin so
	// the umbilical_cord kills it before we start a new instance.
	if managedServerStdin != nil {
		_ = managedServerStdin.Close()
		managedServerStdin = nil
	}

	cmd := exec.Command(pythonPath, "server.py")
	cmd.Env = append(os.Environ(), "ANTI_MANAGED=1")
	cmd.SysProcAttr = &syscall.SysProcAttr{
		Pdeathsig: syscall.SIGKILL,
	}

	r, w, err := os.Pipe()
	if err != nil {
		return fmt.Errorf("pipe: %w", err)
	}
	cmd.Stdin = r

	if logFile, ferr := os.OpenFile("logs/server.log", os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0644); ferr == nil {
		cmd.Stdout = logFile
		cmd.Stderr = logFile
	} else {
		devNull, _ := os.OpenFile(os.DevNull, os.O_WRONLY, 0)
		cmd.Stdout = devNull
		cmd.Stderr = devNull
	}

	if err := cmd.Start(); err != nil {
		_ = r.Close()
		_ = w.Close()
		return fmt.Errorf("start server: %w", err)
	}
	_ = r.Close() // parent doesn't need the read end; child inherited its copy

	if _, err := w.Write(secret); err != nil {
		return fmt.Errorf("send secret: %w", err)
	}

	managedServerStdin = w // keep alive: server monitors stdin
	go func() { _ = cmd.Wait() }()

	return nil
}

func banner() string {
	var sb strings.Builder
	sb.WriteString("  █████  ███    ██ ████████ ██\n")
	sb.WriteString(" ██   ██ ████   ██    ██    ██\n")
	sb.WriteString(" ███████ ██ ██  ██    ██    ██\n")
	sb.WriteString(" ██   ██ ██  ██ ██    ██    ██\n")
	sb.WriteString(" ██   ██ ██   ████    ██    ██\n")
	sb.WriteString(" ─────────────────────────── v1.6\n")
	return sb.String()
}

func (m model) View() string {
	var mainPanel string
	var sidebarPanel string

	// Build Sidebar Panel
	var sb strings.Builder
	sb.WriteString(lipgloss.NewStyle().Foreground(magenta).Bold(true).Render("🧠 ESTADO DE ANTI") + "\n\n")
	
	sb.WriteString(lipgloss.NewStyle().Foreground(purple).Bold(true).Render("🤖 PROVEEDOR SELECCIONADO") + "\n")
	
	activeProv := m.config.Provider
	if activeProv == "" {
		activeProv = "auto"
	}
	
	resolvedProv := activeProv
	switch activeProv {
	case "auto":
		if m.status.LMStudioOnline {
			resolvedProv = "auto (LM Studio ⚡)"
		} else if m.status.OllamaOnline {
			resolvedProv = "auto (Ollama ⚡)"
		} else {
			resolvedProv = "auto (Buscando Local...)"
		}
	case "lmstudio":
		resolvedProv = "LM Studio (Local ⚡)"
	case "ollama":
		resolvedProv = "Ollama (Local ⚡)"
	case "openai":
		resolvedProv = "OpenAI (Nube ☁️)"
	case "gemini":
		resolvedProv = "Gemini (Nube ☁️)"
	case "deepseek":
		resolvedProv = "DeepSeek (Nube ☁️)"
	case "anthropic":
		resolvedProv = "Claude (Nube ☁️)"
	case "minimax":
		resolvedProv = "Minimax (Nube ☁️)"
	case "openaicompatible":
		resolvedProv = "Compatible (Híbrido 🔌)"
	}
	
	sb.WriteString(fmt.Sprintf("%s: %s\n", lipgloss.NewStyle().Foreground(gray).Render("Nombre"), lipgloss.NewStyle().Foreground(cyan).Render(resolvedProv)))

	modelName := m.config.Model
	if modelName == "" {
		if activeProv == "auto" {
			if m.status.LMStudioOnline {
				modelName = "Auto-detectado (LM Studio)"
			} else if m.status.OllamaOnline {
				modelName = "Auto-detectado (Ollama)"
			} else {
				modelName = "Auto-detectado"
			}
		} else {
			modelName = "Auto-detectado"
		}
	}
	sb.WriteString(fmt.Sprintf("%s: %s\n", lipgloss.NewStyle().Foreground(gray).Render("Modelo"), lipgloss.NewStyle().Foreground(cyan).Render(modelName)))

	statusStr := lipgloss.NewStyle().Foreground(gray).Render("Desconectado ❌")
	switch activeProv {
	case "auto":
		if m.status.LMStudioOnline || m.status.OllamaOnline {
			statusStr = lipgloss.NewStyle().Foreground(cyan).Bold(true).Render("Listo (Local) 🟢")
		}
	case "lmstudio":
		if m.status.LMStudioOnline {
			statusStr = lipgloss.NewStyle().Foreground(cyan).Bold(true).Render("Online 🟢")
		} else {
			statusStr = lipgloss.NewStyle().Foreground(magenta).Bold(true).Render("Offline ❌")
		}
	case "ollama":
		if m.status.OllamaOnline {
			statusStr = lipgloss.NewStyle().Foreground(cyan).Bold(true).Render("Online 🟢")
		} else {
			statusStr = lipgloss.NewStyle().Foreground(magenta).Bold(true).Render("Offline ❌")
		}
	case "openai":
		if m.config.OpenAIAPIKey != "" {
			statusStr = lipgloss.NewStyle().Foreground(cyan).Bold(true).Render("Configurado ✅")
		}
	case "gemini":
		if m.config.GeminiAPIKey != "" {
			statusStr = lipgloss.NewStyle().Foreground(cyan).Bold(true).Render("Configurado ✅")
		}
	case "deepseek":
		if m.config.DeepSeekAPIKey != "" {
			statusStr = lipgloss.NewStyle().Foreground(cyan).Bold(true).Render("Configurado ✅")
		}
	case "anthropic":
		if m.config.AnthropicAPIKey != "" {
			statusStr = lipgloss.NewStyle().Foreground(cyan).Bold(true).Render("Configurado ✅")
		}
	case "minimax":
		if m.config.MinimaxAPIKey != "" {
			statusStr = lipgloss.NewStyle().Foreground(cyan).Bold(true).Render("Configurado ✅")
		}
	case "openaicompatible":
		if m.config.OpenAICompatibleAPIKey != "" {
			statusStr = lipgloss.NewStyle().Foreground(cyan).Bold(true).Render("Configurado ✅")
		}
	}
	sb.WriteString(fmt.Sprintf("%s: %s\n\n", lipgloss.NewStyle().Foreground(gray).Render("Conexión"), statusStr))

	sb.WriteString(lipgloss.NewStyle().Foreground(purple).Bold(true).Render("🔌 OTROS DISPONIBLES") + "\n")
	var readyList []string
	if m.status.LMStudioOnline && activeProv != "lmstudio" {
		readyList = append(readyList, "LMStudio")
	}
	if m.status.OllamaOnline && activeProv != "ollama" {
		readyList = append(readyList, "Ollama")
	}
	if m.config.OpenAIAPIKey != "" && activeProv != "openai" {
		readyList = append(readyList, "OpenAI")
	}
	if m.config.GeminiAPIKey != "" && activeProv != "gemini" {
		readyList = append(readyList, "Gemini")
	}
	if m.config.DeepSeekAPIKey != "" && activeProv != "deepseek" {
		readyList = append(readyList, "DeepSeek")
	}
	if m.config.AnthropicAPIKey != "" && activeProv != "anthropic" {
		readyList = append(readyList, "Claude")
	}
	if m.config.MinimaxAPIKey != "" && activeProv != "minimax" {
		readyList = append(readyList, "Minimax")
	}
	if m.config.OpenAICompatibleAPIKey != "" && activeProv != "openaicompatible" {
		readyList = append(readyList, "Custom")
	}

	if len(readyList) == 0 {
		sb.WriteString(lipgloss.NewStyle().Foreground(darkGray).Render("Ninguno extra listo") + "\n\n")
	} else {
		sb.WriteString(lipgloss.NewStyle().Foreground(white).Render(strings.Join(readyList, ", ")) + "\n\n")
	}

	sb.WriteString(fmt.Sprintf("%s: %s\n", lipgloss.NewStyle().Foreground(gray).Render("Workspace Files"), lipgloss.NewStyle().Foreground(white).Render(fmt.Sprintf("%d", m.status.WorkspaceFiles))))
	sb.WriteString(fmt.Sprintf("%s: %s\n\n", lipgloss.NewStyle().Foreground(gray).Render("Base de Conocimiento"), lipgloss.NewStyle().Foreground(white).Render(fmt.Sprintf("%d KB", m.status.EngramsCount))))

	sb.WriteString(lipgloss.NewStyle().Foreground(purple).Bold(true).Render("🐳 SANDBOX") + "\n")
	sandboxBadge := lipgloss.NewStyle().Foreground(magenta).Bold(true).Render("[OFFLINE]")
	if m.status.SandboxOnline {
		sandboxBadge = lipgloss.NewStyle().Foreground(lipgloss.Color("#00ff00")).Bold(true).Render("[ONLINE]")
	}
	sb.WriteString(fmt.Sprintf("%s %s\n", lipgloss.NewStyle().Foreground(gray).Render("Estado:"), sandboxBadge))

	if m.status.SandboxOnline {
		usedMB := m.status.SandboxMemUsedMB
		limMB := m.status.SandboxMemLimMB
		if limMB == 0 {
			limMB = 2048
		}
		pct := float64(usedMB) / float64(limMB)
		if pct > 1 {
			pct = 1
		}
		barWidth := 26
		filled := int(pct * float64(barWidth))
		bar := strings.Repeat("█", filled) + strings.Repeat("░", barWidth-filled)
		barColor := lipgloss.Color("#00ff00")
		if pct > 0.75 {
			barColor = lipgloss.Color("#ff9900")
		}
		if pct > 0.9 {
			barColor = lipgloss.Color("#ff003c")
		}
		sb.WriteString(lipgloss.NewStyle().Foreground(gray).Render("RAM:") + "\n")
		sb.WriteString(lipgloss.NewStyle().Foreground(barColor).Render(bar) + "\n")
		sb.WriteString(lipgloss.NewStyle().Foreground(darkGray).Render(fmt.Sprintf("%dMB / %dMB (%.0f%%)", usedMB, limMB, pct*100)) + "\n")
	}

	engramCount := m.status.BootEngrams
	engramStr := fmt.Sprintf("🧠 Memoria Core: %d Engrams Activos", engramCount)
	engramStyle := lipgloss.NewStyle().Foreground(cyan).Bold(true)
	if engramCount == 0 {
		engramStyle = lipgloss.NewStyle().Foreground(darkGray)
		engramStr = "🧠 Memoria Core: Sin cargar"
	}
	sb.WriteString("\n" + engramStyle.Render(engramStr) + "\n")

	sidebarPanel = sidebarStyle.Render(sb.String())

	switch m.screen {
	case ScreenMain:
		var mainSB strings.Builder
		mainSB.WriteString(lipgloss.NewStyle().Foreground(cyan).Bold(true).Render("💻 PANEL DE CONTROL INTERACTIVO") + "\n\n")

		for i, choice := range m.choices {
			cursorSymbol := "  "
			item := choice
			if m.cursor == i {
				cursorSymbol = "▸ "
				item = selectedItemStyle.Render(choice)
			} else {
				item = normalItemStyle.Render(choice)
			}
			mainSB.WriteString(fmt.Sprintf("%s%s\n", cursorSymbol, item))
		}
		
		mainSB.WriteString("\n" + lipgloss.NewStyle().Foreground(darkGray).Render("↑/↓ j/k navegar • Enter seleccionar"))
		mainSB.WriteString("\n" + lipgloss.NewStyle().Foreground(darkGray).Render("───────────────────────────────"))
		mainSB.WriteString("\n" + lipgloss.NewStyle().Foreground(darkGray).Render("[r] Sandbox  [p] Purgar Logs"))
		mainPanel = mainContentStyle.Render(mainSB.String())

	case ScreenKeys:
		var mainSB strings.Builder
		mainSB.WriteString(lipgloss.NewStyle().Foreground(cyan).Bold(true).Render("🔌 CONFIGURACIÓN DE CLAVES API") + "\n\n")

		keys := []struct {
			num  string
			name string
			val  string
		}{
			{"1", "OpenAI Key", m.config.OpenAIAPIKey},
			{"2", "DeepSeek Key", m.config.DeepSeekAPIKey},
			{"3", "Gemini Key", m.config.GeminiAPIKey},
			{"4", "Anthropic Key", m.config.AnthropicAPIKey},
			{"5", "Minimax Key", m.config.MinimaxAPIKey},
			{"6", "OpenAI Comp Key", m.config.OpenAICompatibleAPIKey},
		}

		for _, k := range keys {
			status := lipgloss.NewStyle().Foreground(gray).Render("No configurada ❌")
			if k.val != "" {
				status = lipgloss.NewStyle().Foreground(cyan).Bold(true).Render("Configurada ✅")
			}
			mainSB.WriteString(fmt.Sprintf("[%s] %s: %s\n", k.num, lipgloss.NewStyle().Foreground(white).Bold(true).Render(k.name), status))
		}

		mainSB.WriteString("\n[0] Volver al Menú Principal\n")
		mainSB.WriteString("\n" + lipgloss.NewStyle().Foreground(darkGray).Render("Presioná un número para editar su clave"))
		mainPanel = mainContentStyle.Render(mainSB.String())

	case ScreenAPIInput:
		var mainSB strings.Builder
		displayName := m.selectedAPI
		if displayName == "openaicompatible" {
			displayName = "compatible"
		}
		mainSB.WriteString(lipgloss.NewStyle().Foreground(cyan).Bold(true).Render(fmt.Sprintf("🔑 CONFIGURAR %s", strings.ToUpper(displayName))) + "\n\n")
		mainSB.WriteString(lipgloss.NewStyle().Foreground(white).Render("Ingresá la clave y presioná Enter:") + "\n\n")
		mainSB.WriteString(m.apiInput.View() + "\n\n")
		mainSB.WriteString(lipgloss.NewStyle().Foreground(darkGray).Render("Presioná Esc para cancelar y volver"))
		mainPanel = mainContentStyle.Render(mainSB.String())

	case ScreenModel:
		var mainSB strings.Builder
		mainSB.WriteString(lipgloss.NewStyle().Foreground(cyan).Bold(true).Render("🤖 PROVEEDOR & MODELO ACTIVO") + "\n\n")
		
		providers := []string{
			"[1] Autodetectar Locales (Auto)",
			"[2] LM Studio (http://localhost:1234)",
			"[3] Ollama (http://localhost:11434)",
			"[4] OpenAI (GPT-4o)",
			"[5] Gemini (Gemini 2.5 Flash)",
			"[6] DeepSeek (DeepSeek Chat)",
			"[7] Anthropic (Claude 3.5 Sonnet)",
			"[8] Minimax (abab6.5g)",
			"[9] OpenAI Compatible (Groq, Together, etc.)",
		}

		for _, p := range providers {
			mainSB.WriteString(p + "\n")
		}

		mainSB.WriteString("\n[0] Volver al Menú Principal\n")
		mainSB.WriteString("\n" + lipgloss.NewStyle().Foreground(darkGray).Render("Selecciona un proveedor ingresando su número"))
		mainPanel = mainContentStyle.Render(mainSB.String())

	case ScreenSetup:
		var mainSB strings.Builder
		mainSB.WriteString(lipgloss.NewStyle().Foreground(cyan).Bold(true).Render("⚙️ DIAGNÓSTICO DEL SISTEMA") + "\n\n")

		filesToCheck := []string{"config.local.json", "config.json", "config.json.example", "requirements.txt", "main.py", "server.py"}
		for _, f := range filesToCheck {
			status := lipgloss.NewStyle().Foreground(cyan).Bold(true).Render("PRESENTE ✅")
			if _, err := os.Stat(f); os.IsNotExist(err) {
				status = lipgloss.NewStyle().Foreground(magenta).Bold(true).Render("FALTANTE ❌")
			}
			mainSB.WriteString(fmt.Sprintf("%s: %s\n", lipgloss.NewStyle().Foreground(white).Render(f), status))
		}

		mainSB.WriteString("\n[0] Volver al Menú Principal\n")
		mainPanel = mainContentStyle.Render(mainSB.String())

	case ScreenChat:
		mainPanel = mainContentStyle.Render(m.chatViewport.View())
	}

	appHeader := titleStyle.Render(banner()) + "\n"
	appPanels := lipgloss.JoinHorizontal(lipgloss.Top, sidebarPanel, "   ", mainPanel)

	if m.screen == ScreenChat {
		hint := lipgloss.NewStyle().Foreground(darkGray).Render("Enter: escribir • ↑/↓ PgUp/PgDn: scroll • Esc: volver")
		if m.viewingResponse {
			hint = lipgloss.NewStyle().Foreground(cyan).Render("↑/↓ PgUp/PgDn: scroll • Enter: escribir nueva pregunta • Esc: volver")
		}
		return appHeader + "\n" + appPanels + "\n\n" + m.chatInput.View() + "\n" + hint
	}

	return appHeader + "\n" + appPanels + "\n\n"
}

func main() {
	if exePath, err := os.Executable(); err == nil {
		appDir := filepath.Dir(exePath)
		_ = os.Chdir(appDir)
	}

	if len(os.Args) > 1 {
		switch os.Args[1] {
		case "--mem-init":
			if err := RunMemBoot(); err != nil {
				fmt.Printf("{\"status\": \"error\", \"message\": \"%v\"}\n", err)
				os.Exit(1)
			}
			os.Exit(0)
		case "--mem-search":
			if len(os.Args) < 3 {
				fmt.Println("[]")
				os.Exit(1)
			}
			if err := RunMemSearch(os.Args[2]); err != nil {
				fmt.Printf("{\"status\": \"error\", \"message\": \"%v\"}\n", err)
				os.Exit(1)
			}
			os.Exit(0)
		case "--mem-get":
			if len(os.Args) < 3 {
				fmt.Println("{\"status\": \"error\", \"message\": \"Falta id de engram\"}")
				os.Exit(1)
			}
			if err := RunMemGet(os.Args[2]); err != nil {
				fmt.Printf("{\"status\": \"error\", \"message\": \"%v\"}\n", err)
				os.Exit(1)
			}
			os.Exit(0)
		case "--mem-distill":
			if err := RunMemDistill(); err != nil {
				fmt.Printf("{\"status\": \"error\", \"message\": \"%v\"}\n", err)
				os.Exit(1)
			}
			os.Exit(0)
		case "--mem-reinforce":
			if len(os.Args) < 3 {
				fmt.Println("{\"status\": \"error\", \"message\": \"Falta id de engram\"}")
				os.Exit(1)
			}
			if err := RunMemReinforce(os.Args[2]); err != nil {
				fmt.Printf("{\"status\": \"error\", \"message\": \"%v\"}\n", err)
				os.Exit(1)
			}
			os.Exit(0)
		default:
			fmt.Printf("Comando desconocido: %s\nUsar: --mem-init, --mem-search, --mem-get, --mem-distill, --mem-reinforce\n", os.Args[1])
			os.Exit(1)
		}
	}

	p := tea.NewProgram(initialModel(), tea.WithAltScreen(), tea.WithMouseCellMotion())
	if _, err := p.Run(); err != nil {
		fmt.Printf("Ocurrió un error en el TUI: %v", err)
		os.Exit(1)
	}
}
