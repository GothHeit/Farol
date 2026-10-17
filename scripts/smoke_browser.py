#!/usr/bin/env python3
"""Smoke opcional de navegador real; usa apenas banco temporário e dados sintéticos.

Pré-requisitos opcionais: pip install playwright; python3 -m playwright install chromium
Execução: python3 scripts/smoke_browser.py
Não altera data/farol.sqlite3. Capturas ficam em /tmp/farol-{mentor,mobile}.png.
"""
from contextlib import closing
from pathlib import Path
import json
import os
import sys
import tempfile
import threading

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
try:
    from playwright.sync_api import sync_playwright, expect
except ImportError:
    raise SystemExit('Smoke opcional: instale playwright e Chromium conforme o cabeçalho deste script.')

from farol.db import connect, migrate, week
from farol.seed import seed
from server import create_server

PASSWORD = 'synthetic-browser-test-only'


def smoke(page, base_url):
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.set_default_timeout(10000)

    def login(email):
        page.goto(base_url)
        expect(page.locator('#login')).to_be_visible()
        expect(page.locator('#senha')).to_have_value('')
        page.locator('#email').fill(email)
        page.locator('#senha').fill(PASSWORD)
        page.locator('#loginForm button').click()
        expect(page.locator('#app')).to_be_visible()
        expect(page.locator('#main')).not_to_have_attribute('aria-busy', 'true')

    def logout():
        if page.locator('#drawer').is_visible():
            page.keyboard.press('Escape')
            expect(page.locator('#drawer')).to_be_hidden()
        page.locator('#logout').click()
        expect(page.locator('#login')).to_be_visible()

    def tab(key):
        page.locator(f'#tab-{key}').click()
        expect(page.locator(f'#tab-{key}')).to_have_attribute('aria-selected', 'true')

    def open_student():
        page.locator('#studentGrid [data-id="student_beatriz"]').click()
        expect(page.locator('#drawerTitle')).to_have_text('Beatriz A.')

    def save_document():
        page.locator('[data-form="document"] button[type="submit"]').click()
        expect(page.locator('[data-form="document"]')).to_have_count(0)

    login('ana@farol.local')
    expect(page.locator('#studentGrid .tile')).to_have_count(8)
    expect(page.locator('.queue-list')).not_to_contain_text('Daniel F.')
    expect(page.locator('.queue-list')).to_contain_text('Pedro H.')
    expect(page.locator('#main')).to_contain_text('Observar · resumo semanal')
    page.screenshot(path='/tmp/farol-mentor.png', full_page=True)
    page.set_viewport_size({'width': 390, 'height': 844})
    page.screenshot(path='/tmp/farol-mobile.png', full_page=True)
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Layout móvel transborda horizontalmente.'
    page.set_viewport_size({'width': 1440, 'height': 1000})
    open_student()
    expect(page.locator('[role="tab"]')).to_have_count(6)
    expect(page.locator('#app')).to_have_attribute('inert', '')
    page.locator('#tab-facts').focus()
    page.keyboard.press('ArrowRight')
    expect(page.locator('#tab-alerts')).to_be_focused()
    page.keyboard.press('End')
    expect(page.locator('#tab-messages')).to_be_focused()
    page.keyboard.press('Tab')
    expect(page.locator('#detailPane')).to_be_focused()
    page.keyboard.press('Escape')
    expect(page.locator('#drawer')).to_be_hidden()
    expect(page.locator('#studentGrid [data-id="student_beatriz"]')).to_be_focused()
    open_student()
    tab('alerts')
    triage = page.locator('[data-form="triage"]').first
    triage.locator('textarea').fill('Interpretação escrita manualmente no teste.')
    triage.locator('[name="useful"]').select_option('true')
    triage.locator('[name="following"]').check()
    triage.locator('button[type="submit"]').click()
    expect(page.locator('[data-form="triage"]').first.locator('button[type="submit"]')).to_be_enabled()
    expect(page.locator('[data-form="triage"]').first.locator('[name="useful"]')).to_have_value('true')

    tab('notes')
    private_text = 'Anotação privada manual <script>window.injection=true</script>'
    page.locator('#note-body').fill(private_text)
    page.context.set_offline(True)
    page.locator('[data-form="note"] button').click()
    expect(page.locator('[data-form="note"] .form-status')).to_contain_text('Sem conexão')
    expect(page.locator('#note-body')).to_have_value(private_text)
    page.context.set_offline(False)
    page.locator('[data-form="note"] button').click()
    expect(page.locator('#detailPane .prose').first).to_have_text(private_text)
    assert page.evaluate('window.injection === undefined'), 'HTML do usuário foi executado.'
    page.locator('[data-action="edit-note"]').click()
    page.locator('#edit-note-body').fill(private_text+' revisada')
    page.locator('[data-form="edit-note"] button').click()
    expect(page.locator('#detailPane .prose').first).to_have_text(private_text+' revisada')
    page.locator('#intervention-body').fill('Conversa registrada manualmente pelo mentor de teste.')
    page.locator('[data-form="intervention"] button').click()
    expect(page.locator('#detailPane')).to_contain_text('Conversa registrada manualmente')

    tab('work')
    page.locator('[data-action="new-document"]').click()
    expect(page.locator('#document-body')).to_have_value('')
    page.locator('#document-title').fill('Plano manual do teste')
    page.locator('#document-body').fill('Orientação escrita pelo mentor, sem texto automático.')
    page.locator('[data-action="add-activity"]').click()
    page.locator('[name="activity_title"]').fill('Atividade manual do teste')
    page.locator('[name="activity_due"]').fill(week())
    activity_id = page.locator('.activity').get_attribute('data-id')
    page.locator('#document-status').select_option('published')
    save_document()
    expect(page.locator('#detailPane')).to_contain_text('Atividade manual do teste')
    page.locator('[data-action="edit-document"]').click()
    expect(page.locator('.activity')).to_have_attribute('data-id', activity_id)
    page.locator('[name="activity_title"]').fill('Atividade manual revisada')
    save_document()
    tasks = page.locator('#detailPane table tbody tr').filter(has_text='Atividade manual revisada')
    expect(tasks).to_have_count(1)

    tab('reports')
    page.locator('[data-action="new-document"]').click()
    expect(page.locator('#document-body')).to_have_value('')
    page.locator('#document-title').fill('Relatório semanal manual')
    page.locator('#document-body').fill('Texto factual escrito pelo mentor no teste.')
    save_document()
    page.locator('[data-action="edit-document"]').click()
    page.locator('#document-status').select_option('reviewed')
    save_document()
    page.locator('[data-action="edit-document"]').click()
    page.locator('#document-status').select_option('published')
    save_document()
    expect(page.locator('#detailPane .document .label')).to_have_text('Publicado')
    page.locator('[data-action="edit-document"]').click()
    expect(page.locator('#document-status')).to_have_value('draft')
    page.locator('[data-action="cancel-document"]').click()

    tab('messages')
    expect(page.locator('#message-body')).to_have_value('')
    page.locator('#message-body').fill('Mensagem manual do mentor no teste.')
    page.locator('[data-form="message"] button').click()
    expect(page.locator('#detailPane')).to_contain_text('Mensagem manual do mentor no teste.')
    logout()

    login('beatriz@farol.local')
    expect(page.locator('#main')).to_contain_text('Relatório semanal manual')
    expect(page.locator('#main')).not_to_contain_text('Anotação privada manual')
    task_row = page.locator('tr').filter(has_text='Atividade manual revisada')
    task_row.locator('select').select_option('done')
    expect(page.locator('tr').filter(has_text='Atividade manual revisada').locator('select')).to_be_enabled()
    expect(page.locator('tr').filter(has_text='Atividade manual revisada').locator('select')).to_have_value('done')
    logout()

    login('ana@farol.local')
    open_student()
    tab('work')
    expect(page.locator('tr').filter(has_text='Atividade manual revisada')).to_contain_text('Concluída')
    expect(page.locator('tr').filter(has_text='Atividade manual revisada')).to_contain_text('Atualizada por Beatriz A.')
    logout()

    login('responsavel@farol.local')
    expect(page.locator('#main')).to_contain_text('Relatório semanal manual')
    expect(page.locator('#main')).not_to_contain_text('Plano manual do teste')
    logout()

    login('admin@farol.local')
    page.locator('[data-action="new-version"]').click()
    page.locator('#version-name').fill('Rascunho do smoke')
    page.locator('#version-reason').fill('Validação do fluxo administrativo sintético.')
    config = json.loads(page.locator('#version-config').input_value())
    config['rules'][0]['threshold'] = 9
    page.locator('#version-config').fill(json.dumps(config, ensure_ascii=False))
    page.locator('[data-form="version"] button[type="submit"]').click()
    expect(page.locator('#versionEditor h2')).to_have_text('Rascunho do smoke')
    page.locator('[data-action="validate-version"]').click()
    expect(page.locator('#ruleResult')).to_contain_text('Configuração válida')
    page.locator('[data-action="simulate-version"]').click()
    expect(page.locator('#ruleResult')).to_contain_text('Comparação da simulação')
    expect(page.locator('#ruleResult table tbody tr')).to_have_count(9)
    page.locator('#version-reason').fill('Ativação da configuração de teste.')
    page.locator('[data-action="activate-version"]').click()
    expect(page.locator('#versionEditor .label').first).to_have_text('Ativa')
    page.locator('.version').last.click()
    page.locator('#version-reason').fill('Restauração da versão anterior para teste.')
    page.locator('[data-action="restore-version"]').click()
    expect(page.locator('#versionEditor h2')).to_contain_text('Restauração')
    expect(page.locator('#versionEditor .label').first).to_have_text('Ativa')
    page.locator('[data-action="assignments"]').click()
    expect(page.locator('[data-form="assignment"]')).to_have_count(9)
    page.keyboard.press('Escape')
    page.locator('[data-action="audit"]').click()
    expect(page.locator('#drawer')).to_contain_text('rules.activate')
    assert not errors, 'Erros JavaScript: '+str(errors)
    print('PASS: login, carteira, responsividade, foco, abas, triagem, nota/revisão, intervenção, plano/tarefa, relatório, aluno, responsável, admin, simulação, ativação/restauração, auditoria, escape HTML.')


def main():
    # O cookie Secure só se aplica à instalação HTTPS, não ao servidor isolado deste teste.
    os.environ['FAROL_SECURE_COOKIE'] = 'false'
    with tempfile.TemporaryDirectory(prefix='farol-browser-') as tmp:
        db_path = Path(tmp) / 'test.sqlite3'
        migrate(db_path)
        with closing(connect(db_path)) as db, db:
            seed(db, password=PASSWORD)
        server = create_server(db_path, port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(viewport={'width': 1440, 'height': 1000}, reduced_motion='reduce')
                smoke(context.new_page(), f'http://127.0.0.1:{server.server_address[1]}')
                browser.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == '__main__':
    main()
