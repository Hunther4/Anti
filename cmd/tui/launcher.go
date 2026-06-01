package main

import (
	crypto_rand "crypto/rand"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"syscall"
	"time"

	"github.com/charmbracelet/bubbles/textinput"
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

	// boxStyle reserved for future modal dialogs

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
	cursor       int
	choices      []string
	config       Config
	status       ModelStatus
	screen       Screen
	selectedAPI  string
	apiInput     textinput.Model
	chatInput    textinput.Model
	chatHistory  []string
	activeJobId  string
	err          error
	quitting     bool
	pythonPath   string
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

		resp, err := http.Post(url, "application/json", strings.NewReader(string(body)))
		if err != nil {
			return chatErrorMsg{err: err}
		}
		defer resp.Body.Close()

		var res map[string]string
		if err := json.NewDecoder(resp.Body).Decode(&res); err != nil {
			return chatErrorMsg{err: err}
		}
		return chatJobIdMsg{jobId: res["job_id"]}
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

		status := res["status"].(string)
		if status == "completed" {
			result := res["result"].(map[string]interface{})
			return chatResponseMsg{response: result["response"].(string)}
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

	ci := textinput.New()
	ci.Placeholder = "Escribe un mensaje para Anti..."
	ci.Focus()

	// Determine correct python command inside venv
	pythonPath := "./venv/bin/python"
	if _, err := os.Stat(pythonPath); os.IsNotExist(err) {
		pythonPath = "python3"
	}

	m := model{
		choices: []string{
			"🖥️  Terminal (Ejecutar Anti)",
			"🌐  Web Host (Servidor Interactivo)",
			"🔌  Conexiones API (Gestionar Claves)",
			"🤖  Elegir Modelo (Seleccionar IA)",
			"⚙️  Instalación & Setup (Diagnóstico)",
			"🐳  Reiniciar Sandbox (Docker)",
			"🚪  Salir",
		},
		screen:     ScreenMain,
		apiInput:   ti,
		chatInput:  ci,
		pythonPath: pythonPath,
	}

	m.loadConfig()
	m.checkStatus()
	return m
}

func (m *model) loadConfig() {
	configPath := "config.json"
	file, err := os.ReadFile(configPath)
	if err != nil {
		m.config = Config{
			AgentName:   "Anti",
			Language:    "es",
			Provider:    "auto",
			LMStudioURL: "http://127.0.0.1:1234/v1",
			OllamaURL:   "http://127.0.0.1:11434",
		}
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
	configPath := "config.json"
	data, err := json.MarshalIndent(m.config, "", "  ")
	if err != nil {
		m.err = err
		return
	}
	_ = os.WriteFile(configPath, data, 0644)
}

func (m *model) checkStatus() {
	// 1. Check workspace files count
	files, _ := filepath.Glob("workspace/*")
	m.status.WorkspaceFiles = len(files)

	// 2. Simple engram database size or count
	dbPath := "memory/cold_archive.db"
	if fi, err := os.Stat(dbPath); err == nil {
		m.status.EngramsCount = int(fi.Size() / 1024) // size in KB as simple indicator
	}

	// Read cached boot_payload to get active engrams count
	if data, err := os.ReadFile("memory/boot_payload.json"); err == nil {
		var bp struct {
			BootEngramsCount int `json:"boot_engrams_count"`
		}
		if json.Unmarshal(data, &bp) == nil {
			m.status.BootEngrams = bp.BootEngramsCount
		}
	}

	// 3. Ping local providers in background or quickly with healthy timeout
	client := http.Client{Timeout: 750 * time.Millisecond}
	
	lmURL := m.config.LMStudioURL
	if lmURL == "" {
		lmURL = "http://127.0.0.1:1234/v1"
	}
	resp, err := client.Get(lmURL + "/models")
	if err == nil && resp != nil {
		m.status.LMStudioOnline = resp.StatusCode == 200
		_ = resp.Body.Close()
	} else {
		m.status.LMStudioOnline = false
	}

	ollamaURL := m.config.OllamaURL
	if ollamaURL == "" {
		ollamaURL = "http://127.0.0.1:11434"
	}
	resp2, err2 := client.Get(ollamaURL + "/api/tags")
	if err2 == nil && resp2 != nil {
		m.status.OllamaOnline = resp2.StatusCode == 200
		_ = resp2.Body.Close()
	} else {
		m.status.OllamaOnline = false
	}

	// 4. Check Sandbox state
	sandboxCheckCmd := exec.Command("docker", "inspect", "-f", "{{.State.Running}}", "anti-sandbox")
	if out, err := sandboxCheckCmd.Output(); err == nil {
		m.status.SandboxOnline = strings.TrimSpace(string(out)) == "true"
	} else {
		m.status.SandboxOnline = false
	}
}

func (m model) Init() tea.Cmd {
	return tea.Batch(
		textinput.Blink,
		tickSandboxStats(),
	)
}

func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	var cmd tea.Cmd

	switch msg := msg.(type) {
	case sandboxStatsMsg:
		m.status.SandboxOnline = msg.online
		m.status.SandboxMemUsedMB = msg.usedMB
		m.status.SandboxMemLimMB = msg.limMB
		return m, tickSandboxStats()
	case chatJobIdMsg:
		m.activeJobId = msg.jobId
		return m, m.pollJobStatus(msg.jobId)
	case chatResponseMsg:
		m.chatHistory = append(m.chatHistory, "Anti: "+msg.response)
		m.activeJobId = ""
		return m, nil
	case chatErrorMsg:
		m.chatHistory = append(m.chatHistory, "Error: "+msg.err.Error())
		m.activeJobId = ""
		return m, nil
	case pollContinueMsg:
		if m.activeJobId != "" {
			return m, m.pollJobStatus(m.activeJobId)
		}
		return m, nil
	case sandboxResetMsg:
		m.checkStatus()
		if msg.err != nil {
			m.err = msg.err
		} else {
			m.err = nil
		}
		return m, nil
	case processFinishedMsg:
		m.checkStatus()
		return m, nil
	case tea.KeyMsg:
		switch msg.Type {
		case tea.KeyCtrlC, tea.KeyEsc:
			if m.screen != ScreenMain {
				m.screen = ScreenMain
				m.apiInput.Reset()
				m.chatInput.Reset()
				m.checkStatus()
				return m, nil
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
				choice := m.choices[m.cursor]
				if strings.Contains(choice, "Terminal") {
					m.screen = ScreenChat
					m.chatInput.Focus()
					return m, func() tea.Msg {
						cmd := exec.Command("python3", "server.py")
						cmd.Start()
						return processFinishedMsg{}
					}
				} else if strings.Contains(choice, "API") {
					m.screen = ScreenAPIInput
					m.apiInput.Focus()
					return m, nil
				} else if strings.Contains(choice, "Modelo") {
					m.screen = ScreenModel
					return m, nil
				} else if strings.Contains(choice, "Instalación") {
					m.screen = ScreenSetup
					return m, nil
				} else if strings.Contains(choice, "Sandbox") {
					return m, doResetSandbox(".")
				} else if strings.Contains(choice, "Salir") {
					m.quitting = true
					return m, tea.Quit
				}
			}
		} else if m.screen == ScreenChat {
			switch msg.Type {
			case tea.KeyEnter:
				input := m.chatInput.Value()
				if input == "" {
					return m, nil
				}
				m.chatHistory = append(m.chatHistory, "User: "+input)
				m.chatInput.SetValue("")
				m.activeJobId = ""
				return m, m.sendChatMessage(input)
			}
			return m, m.chatInput.Update(msg)
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
				m.checkStatus()
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
			}
		}
	}

	return m, cmd
}
		return m, nil
	case sandboxResetMsg:
		m.checkStatus()
		if msg.err != nil {
			m.err = msg.err
		} else {
			m.err = nil
		}
		return m, nil
	case processFinishedMsg:
		m.checkStatus()
		return m, nil
	case tea.KeyMsg:
		switch msg.Type {
		case tea.KeyCtrlC, tea.KeyEsc:
			if m.screen != ScreenMain {
				m.screen = ScreenMain
				m.apiInput.Reset()
				m.chatInput.Reset()
				m.checkStatus()
				return m, nil
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
				choice := m.choices[m.cursor]
				if strings.Contains(choice, "Terminal") {
					// Start server and go to chat
					m.screen = ScreenChat
					m.chatInput.Focus()
					return m, func() tea.Msg {
						cmd := exec.Command("python3", "server.py")
						cmd.Start()
						return processFinishedMsg{}
					}
				} else if strings.Contains(choice, "API") {
					m.screen = ScreenAPIInput
					m.apiInput.Focus()
					return m, nil
				} else if strings.Contains(choice, "Modelo") {
					m.screen = ScreenModel
					return m, nil
				} else if strings.Contains(choice, "Instalación") {
					m.screen = ScreenSetup
					return m, nil
				} else if strings.Contains(choice, "Sandbox") {
					return m, doResetSandbox(".")
				} else if strings.Contains(choice, "Salir") {
					m.quitting = true
					return m, tea.Quit
				}
			}
		} else if m.screen == ScreenChat {
			switch msg.Type {
			case tea.KeyEnter:
				input := m.chatInput.Value()
				if input == "" {
					return m, nil
				}
				m.chatHistory = append(m.chatHistory, "User: "+input)
				m.chatInput.SetValue("")
				m.activeJobId = ""
				return m, m.sendChatMessage(input)
			}
			return m, m.chatInput.Update(msg)
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
			case "r":
				cwd, _ := os.Getwd()
				_ = ResetSandbox(cwd)
				m.checkStatus()
			case "p":
				_ = os.Remove("memory/logs.jsonl")
			case "enter":
				return m.handleMainMenuSelection()
			}
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
				m.checkStatus()
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
				m.checkStatus()
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
				m.checkStatus()
			}
			m.apiInput, cmd = m.apiInput.Update(msg)
			return m, cmd
		} else if m.screen == ScreenSetup {
			switch msg.String() {
			case "enter", "esc", "b", "0":
				m.screen = ScreenMain
				m.checkStatus()
			}
		}
	}

	return m, nil
}

func (m model) handleMainMenuSelection() (tea.Model, tea.Cmd) {
	switch m.cursor {
	case 0: // Terminal Client
		return m, tea.ExecProcess(exec.Command(m.pythonPath, "main.py"), func(err error) tea.Msg {
			return processFinishedMsg{}
		})
	case 1: // Web Host
		cmd := exec.Command(m.pythonPath, "server.py")
		cmd.Env = append(os.Environ(), "ANTI_MANAGED=1")
		
		r, w, err := os.Pipe()
		if err == nil {
			cmd.Stdin = r
			cmd.SysProcAttr = &syscall.SysProcAttr{
				Pdeathsig: syscall.SIGKILL,
			}
			go func() {
				secret := make([]byte, 32)
				crypto_rand.Read(secret)
				// Guardar el secreto en memoria de Go por si luego queremos hacer llamadas HTTP firmadas
				// os.Setenv("ANTI_SECRET", hex.EncodeToString(secret)) // Opcional
				w.Write(secret)
				// Mantenemos 'w' abierto como cordón umbilical
			}()
		}

		return m, tea.ExecProcess(cmd, func(err error) tea.Msg {
			if w != nil {
				w.Close()
			}
			return processFinishedMsg{}
		})
	case 2: // API Keys Management
		m.screen = ScreenKeys
	case 3: // Model / Provider Selection
		m.screen = ScreenModel
	case 4: // Setup / Diagnostics
		m.screen = ScreenSetup
	case 5: // Docker Sandbox Reset
		cwd, _ := os.Getwd()
		return m, doResetSandbox(cwd)
	case 6: // Exit
		m.quitting = true
		return m, tea.Quit
	}
	return m, nil
}

// Banner rendering
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
	if m.screen == ScreenMain {
		return m.viewMain()
	} else if m.screen == ScreenChat {
		return m.viewChat()
	} else if m.screen == ScreenAPIInput {
		return m.viewAPIInput()
	} else if m.screen == ScreenModel {
		return m.viewModel()
	} else if m.screen == ScreenSetup {
		return m.viewSetup()
	}
	return "Error: Unknown Screen"
}

func (m model) viewChat() string {
	var chatArea strings.Builder
	for _, msg := range m.chatHistory {
		if strings.HasPrefix(msg, "User: ") {
			chatArea.WriteString(fmt.Sprintf("[cyan]User:[/]\n%s\n\n", msg[6:]))
		} else if strings.HasPrefix(msg, "Anti: ") {
			chatArea.WriteString(fmt.Sprintf("[magenta]Anti:[/]\n%s\n\n", msg[6:]))
		} else {
			chatArea.WriteString(fmt.Sprintf("[yellow]%s[/]\n\n", msg))
		}
	}
	if m.activeJobId != "" {
		chatArea.WriteString("[yellow]Anti is thinking...[/]\n")
	}

	content := mainContentStyle.Render(chatArea.String())
	input := m.chatInput.View()
	
	header := titleStyle.Render("ANTI CHAT")
	return fmt.Sprintf("%s\n%s\n\n%s", header, content, input)
}

	var mainPanel string
	var sidebarPanel string

	// Build Sidebar Panel (Dynamic, Compact & Clean)
	var sb strings.Builder
	sb.WriteString(lipgloss.NewStyle().Foreground(magenta).Bold(true).Render("🧠 ESTADO DE ANTI") + "\n\n")
	
	// 1. ACTIVE PROVIDER CARD
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

	// Connection status of ACTIVE provider
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

	// 2. COMPACT READY SERVICES (Only what is ready and not active)
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

	// 3. STATS
	sb.WriteString(fmt.Sprintf("%s: %s\n", lipgloss.NewStyle().Foreground(gray).Render("Workspace Files"), lipgloss.NewStyle().Foreground(white).Render(fmt.Sprintf("%d", m.status.WorkspaceFiles))))
	sb.WriteString(fmt.Sprintf("%s: %s\n\n", lipgloss.NewStyle().Foreground(gray).Render("Base de Conocimiento"), lipgloss.NewStyle().Foreground(white).Render(fmt.Sprintf("%d KB", m.status.EngramsCount))))

	// 4. SANDBOX TELEMETRY PANEL
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

	// Build Main Panel based on current screen
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

		filesToCheck := []string{"config.json", "requirements.txt", "main.py", "server.py"}
		for _, f := range filesToCheck {
			status := lipgloss.NewStyle().Foreground(cyan).Bold(true).Render("PRESENTE ✅")
			if _, err := os.Stat(f); os.IsNotExist(err) {
				status = lipgloss.NewStyle().Foreground(magenta).Bold(true).Render("FALTANTE ❌")
			}
			mainSB.WriteString(fmt.Sprintf("%s: %s\n", lipgloss.NewStyle().Foreground(white).Render(f), status))
		}

		mainSB.WriteString("\n[0] Volver al Menú Principal\n")
		mainPanel = mainContentStyle.Render(mainSB.String())
	}

	// Join banner + panels
	appHeader := titleStyle.Render(banner()) + "\n"
	appPanels := lipgloss.JoinHorizontal(lipgloss.Top, sidebarPanel, "   ", mainPanel)

	return appHeader + "\n" + appPanels + "\n\n"
}

func main() {
	// Asegurar que el proceso siempre se ejecute en el directorio donde reside el binario
	if exePath, err := os.Executable(); err == nil {
		appDir := filepath.Dir(exePath)
		_ = os.Chdir(appDir)
	}

	// Interceptar argumentos del CLI de memoria
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

	p := tea.NewProgram(initialModel(), tea.WithAltScreen())
	if _, err := p.Run(); err != nil {
		fmt.Printf("Ocurrió un error en el TUI: %v", err)
		os.Exit(1)
	}
}
