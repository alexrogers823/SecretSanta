// Checks on config files that Phase 2 changed (2.3, 2.4, 2.10, 2.11), so a later edit can't
// silently undo them
const fs = require('fs')
const path = require('path')

const clientRoot = path.join(__dirname, '..')
const read = file => fs.readFileSync(path.join(clientRoot, file), 'utf8')
const readEnv = file => Object.fromEntries(
  read(file).split('\n')
    .filter(line => line.trim() && !line.startsWith('#'))
    .map(line => [line.slice(0, line.indexOf('=')), line.slice(line.indexOf('=') + 1)])
)

test('npm start proxies /api to Flask on port 8000 (2.3)', () => {
  expect(JSON.parse(read('package.json')).proxy).toBe('http://localhost:8000')
})

test('the Firebase SDK is a dependency (2.3)', () => {
  expect(JSON.parse(read('package.json')).dependencies.firebase).toBeDefined()
})

test.each(['.env.development', '.env.production'])('%s has every Firebase setting and the assets URL (2.4, 2.10)', file => {
  const env = readEnv(file)
  for (const key of ['REACT_APP_FIREBASE_API_KEY', 'REACT_APP_FIREBASE_AUTH_DOMAIN', 'REACT_APP_FIREBASE_PROJECT_ID', 'REACT_APP_FIREBASE_APP_ID']) {
    expect(env[key]).toBeTruthy()
  }
  expect(env.REACT_APP_ASSETS_URL).toBe('https://storage.googleapis.com/secret-santa-assets')
})

test('only development uses the Auth emulator (2.4)', () => {
  expect(readEnv('.env.development').REACT_APP_USE_AUTH_EMULATOR).toBe('true')
  expect(readEnv('.env.production').REACT_APP_USE_AUTH_EMULATOR).toBeUndefined()
})

test('no secrets in the browser env files', () => {
  // Everything in these files ships in the browser bundle, so only public identifiers belong here
  for (const file of ['.env.development', '.env.production']) {
    const keys = Object.keys(readEnv(file))
    expect(keys.filter(key => /SMTP|PASSWORD|SECRET|PRIVATE_KEY|TOKEN/i.test(key))).toEqual([])
    expect(keys.every(key => key.startsWith('REACT_APP_'))).toBe(true)
  }
})

test('the page title and manifest say Secret Santa (2.11)', () => {
  expect(read('public/index.html')).toContain('<title>Secret Santa</title>')
  expect(read('public/index.html')).not.toContain('create-react-app')
  const manifest = JSON.parse(read('public/manifest.json'))
  expect(manifest.name).toBe('Secret Santa')
  expect(manifest.short_name).toBe('Secret Santa')
})

test('theme images are no longer bundled (2.10)', () => {
  expect(fs.existsSync(path.join(clientRoot, 'src', 'assets'))).toBe(false)
  for (const image of ['background.webp', 'ornament.webp', 'christmas-tree.webp']) {
    expect(fs.existsSync(path.join(clientRoot, 'theme-images', image))).toBe(true)
  }
})

test('no code calls the Flask server directly instead of through apiFetch (2.2)', () => {
  const sourceFiles = []
  const walk = dir => fs.readdirSync(dir, { withFileTypes: true }).forEach(entry => {
    const full = path.join(dir, entry.name)
    if (entry.isDirectory()) walk(full)
    else if (/\.js$/.test(entry.name) && !/\.test\.js$/.test(entry.name)) sourceFiles.push(full)
  })
  walk(path.join(clientRoot, 'src'))
  const offenders = sourceFiles.filter(file => fs.readFileSync(file, 'utf8').includes('localhost:8000'))
  expect(offenders).toEqual([])
})
