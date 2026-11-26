"""Execute the generated browser script with dates in several local timezones."""

import json
import os
import re
import shutil
import subprocess
import unittest

from scripts.github_pages import create_parish_index


HARNESS = r'''
const fs = require('node:fs');
const vm = require('node:vm');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
function element() {
  return {hidden: true, disabled: false, children: [], listeners: {},
    appendChild(child) { this.children.push(child); },
    replaceChildren(...children) { this.children = children; },
    addEventListener(event, handler) { this.listeners[event] = handler; }};
}
const ids = Object.fromEntries(['previous-sheet', 'next-sheet', 'home-sheet', 'sheet-date',
  'sheet-status', 'sheet-content', 'sheet-navigation', 'sheet-qr', 'sheets']
  .map(id => [id, element()]));
const sheets = input.days.map(day => ({...element(), dataset: {date: day},
  details: {open: false, day}, querySelector(selector) {
    return selector === 'details' ? this.details : {getAttribute() { return day + '/'; }};
  }}));
class BrowserDate extends Date {
  constructor(...args) { super(...(args.length ? args : [input.now])); }
}
vm.runInNewContext(input.script, {
  Date: BrowserDate, Intl,
  document: {querySelectorAll() { return sheets; },
    getElementById(id) { return ids[id]; }, createElement: element}
});
const snapshots = [];
function snapshot() {
  snapshots.push({src: ids['sheet-content'].src, title: ids['sheet-content'].title,
    status: ids['sheet-status'].textContent, statusHidden: ids['sheet-status'].hidden,
    previousDisabled: ids['previous-sheet'].disabled, nextDisabled: ids['next-sheet'].disabled,
    homeDisabled: ids['home-sheet'].disabled, frameHidden: ids['sheet-content'].hidden,
    listHidden: ids.sheets.hidden, qrDay: ids['sheet-qr'].children[0]?.day,
    options: ids['sheet-date'].children.map(option => option.value)});
}
snapshot();
for (const action of input.actions) {
  if (action.date) {
    ids['sheet-date'].value = action.date;
    ids['sheet-date'].listeners.change();
  } else {
    ids[action.id].listeners.click();
  }
  snapshot();
}
process.stdout.write(JSON.stringify(snapshots));
'''


@unittest.skipUnless(shutil.which('node'), 'Node.js is required to execute the browser script')
class ParishNavigationTests(unittest.TestCase):
    def run_browser(self, now, days=None, actions=(), timezone='Europe/Paris'):
        html = create_parish_index('Saint-Pierre', days if days is not None else [
            '2026-11-22', '2026-11-28', '2026-12-13']).decode()
        result = subprocess.run(
            ['node', '-e', HARNESS], input=json.dumps({
                'script': re.search(r'<script>(.*?)</script>', html, re.S)[1],
                'days': re.findall(r'<li data-date="([^"]+)"', html),
                'now': now, 'actions': actions,
            }), text=True, encoding='utf-8', capture_output=True, check=True,
            env={**os.environ, 'TZ': timezone},
        )
        return json.loads(result.stdout)

    def test_upcoming_sheet_is_shown_with_navigation_and_date_picker(self):
        states = self.run_browser('2026-11-26T12:00:00Z', actions=[
            {'id': 'next-sheet'}, {'id': 'previous-sheet'},
            {'date': '2026-11-22'}, {'id': 'home-sheet'},
        ])
        self.assertEqual([state['src'] for state in states], [
            '2026-11-28/', '2026-12-13/', '2026-11-28/', '2026-11-22/', '2026-11-28/'])
        self.assertEqual(states[0]['status'], '')
        self.assertTrue(states[0]['statusHidden'])
        self.assertIn('samedi 28 novembre 2026', states[0]['title'])
        self.assertTrue(states[0]['listHidden'])
        self.assertEqual([state['qrDay'] + '/' for state in states], [state['src'] for state in states])
        self.assertFalse(states[0]['frameHidden'])
        self.assertEqual(states[0]['options'], ['2026-11-22', '2026-11-28', '2026-12-13'])
        self.assertTrue(states[1]['nextDisabled'])
        self.assertTrue(states[3]['previousDisabled'])
        self.assertFalse(states[3]['homeDisabled'])
        self.assertTrue(states[4]['homeDisabled'])

    def test_browser_local_day_is_kept_until_midnight(self):
        for now, timezone in [('2026-11-28T23:30:00Z', 'America/New_York'),
                              ('2026-11-27T23:30:00Z', 'Europe/Paris')]:
            with self.subTest(timezone=timezone):
                state = self.run_browser(now, timezone=timezone)[0]
                self.assertEqual(state['src'], '2026-11-28/')
                self.assertEqual(state['status'], '')
                self.assertTrue(state['statusHidden'])
        self.assertEqual(self.run_browser('2026-11-29T00:00:00+01:00')[0]['src'], '2026-12-13/')

    def test_all_past_single_future_year_boundary_and_empty(self):
        states = self.run_browser('2027-01-01T12:00:00Z', actions=[
            {'id': 'previous-sheet'}, {'id': 'home-sheet'}])
        self.assertEqual(states[-1]['src'], '2026-12-13/')
        state = states[0]
        self.assertEqual(state['src'], '2026-12-13/')
        self.assertIn('Aucune feuille à venir', state['status'])
        self.assertFalse(state['statusHidden'])
        for now in ['2026-12-31T12:00:00Z', '2027-01-04T12:00:00Z']:
            state = self.run_browser(now, days=['2027-01-03'])[0]
            self.assertEqual(state['src'], '2027-01-03/')
            self.assertTrue(state['previousDisabled'])
            self.assertTrue(state['nextDisabled'])
        self.assertTrue(self.run_browser('2026-11-26T12:00:00Z', days=[])[0]['frameHidden'])
