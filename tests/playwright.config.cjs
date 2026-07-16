module.exports = {
  testDir: __dirname,
  timeout: 90_000,
  expect: { timeout: 10_000 },
  workers: 1,
  use: {
    headless: true,
    viewport: { width: 1440, height: 900 },
  },
};
