package main

import (
	"testing"

	tea "github.com/charmbracelet/bubbletea"
)

func TestInitialModel(t *testing.T) {
	m := initialModel()

	expectedChoices := 6
	if len(m.choices) != expectedChoices {
		t.Errorf("expected %d menu choices, got %d", expectedChoices, len(m.choices))
	}

	if m.screen != ScreenMain {
		t.Errorf("expected initial screen to be ScreenMain, got %v", m.screen)
	}

	if m.cursor != 0 {
		t.Errorf("expected initial cursor to be 0, got %d", m.cursor)
	}
}

func TestCursorNavigation(t *testing.T) {
	m := initialModel()
	m.cursor = 0

	// 1. Move cursor down with "j"
	updated, _ := m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("j")})
	m = updated.(model)
	if m.cursor != 1 {
		t.Errorf("expected cursor to be 1 after pressing 'j', got %d", m.cursor)
	}

	// 2. Move cursor up with "k"
	updated, _ = m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("k")})
	m = updated.(model)
	if m.cursor != 0 {
		t.Errorf("expected cursor to be 0 after pressing 'k', got %d", m.cursor)
	}

	// 3. Test wrap-around when pressing "up" from 0
	updated, _ = m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("k")})
	m = updated.(model)
	expectedLastIdx := len(m.choices) - 1
	if m.cursor != expectedLastIdx {
		t.Errorf("expected cursor to wrap around to %d when pressing 'k' at 0, got %d", expectedLastIdx, m.cursor)
	}
}

func TestScreenTransitions(t *testing.T) {
	m := initialModel()
	
	// Switch screen to ScreenKeys manually to test key configuration navigation
	m.screen = ScreenKeys

	// Pressing '2' should select DeepSeek API and transition to ScreenAPIInput
	updated, _ := m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("2")})
	m = updated.(model)

	if m.selectedAPI != "deepseek" {
		t.Errorf("expected selected API to be 'deepseek', got %s", m.selectedAPI)
	}

	if m.screen != ScreenAPIInput {
		t.Errorf("expected screen to transition to ScreenAPIInput, got %v", m.screen)
	}
}
