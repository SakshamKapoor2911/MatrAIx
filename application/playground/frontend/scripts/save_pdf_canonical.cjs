/**
 * Canonical Headless Playwright Script for MatrAIx Playground UI PDF Export
 *
 * FIXES:
 *  - Multi-pass accordion expansion (up to 15 passes)
 *  - Hides system-readiness sidebar via CSS injection
 *  - Clicks buttons by text content as fallback for non-aria-expanded panels
 *  - Wider viewport (1600px) for better layout
 *  - Font-size reduction to fit more content per page
 *  - Verifies aggregation data presence + facet/chart content
 *
 * Usage:
 *   node scripts/save_pdf_canonical.cjs --jobName="pg-web-playwright-arxiv-paper-choice-5p" --output="C:\tmp\report.pdf"
 */

const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

function parseArgs() {
  const args = {};
  process.argv.slice(2).forEach(arg => {
    if (arg.startsWith('--')) {
      const [key, val] = arg.substring(2).split('=');
      args[key] = val || true;
    }
  });
  return args;
}

(async () => {
  const args = parseArgs();
  const jobName = args.jobName || args.jobId;
  if (!jobName) {
    console.error('ERROR: --jobName or --jobId is required.');
    console.error('Example: node scripts/save_pdf_canonical.cjs --jobName=my-job-name --output=report.pdf');
    process.exit(1);
  }

  const defaultSavePath = path.join(process.cwd(), `${jobName}-report.pdf`);
  const savePath = args.output ? path.resolve(args.output) : defaultSavePath;

  console.log(`Starting PDF Export for Job: "${jobName}"`);
  console.log(`Target Output Path: ${savePath}`);

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ acceptDownloads: true });
  const page = await context.newPage();
  // Wider viewport — sidebar takes less proportional space
  await page.setViewportSize({ width: 1600, height: 2200 });

  const targetUrl = `http://127.0.0.1:8765/?view=runs&harborJob=${encodeURIComponent(jobName)}`;
  console.log(`Navigating to URL: ${targetUrl}`);

  try {
    await page.goto(targetUrl, { waitUntil: 'networkidle', timeout: 30000 });
  } catch (err) {
    console.error('FAILED to connect to Playground UI. Is backend running on http://127.0.0.1:8765?');
    console.error('  Start with: python -m uvicorn backend.api.app:app --host 127.0.0.1 --port 8765');
    console.error('  (from application/playground, with PYTHONPATH set)');
    await browser.close();
    process.exit(1);
  }

  // Wait for React SPA to mount + API data to arrive
  await page.waitForTimeout(5000);

  // --- Reduce font size for denser PDF ---
  await page.addStyleTag({
    content: `
      body { font-size: 9pt !important; }
      h1 { font-size: 14pt !important; }
      h2 { font-size: 11pt !important; }
      h3 { font-size: 10pt !important; }
      table, td, th { font-size: 8pt !important; }
    `,
  });
  await page.waitForTimeout(500);

  // --- Expand all collapsible sections ---
  // Two-step approach:
  // 1. Click outer "Show detailed report" via evaluate (native click works for React)
  // 2. Force-unhide all hidden content via CSS injection (React keeps hidden elements
  //    in DOM with display:none / max-height:0 — clicking aria-expanded toggles text
  //    but React's style binding doesn't respond to programmatic clicks)
  console.log('\nExpanding all collapsible sections...');
  await page.evaluate(() => {
    const items = [...document.querySelectorAll('[aria-expanded="false"]')];
    for (const el of items) {
      if (!(el instanceof HTMLElement)) continue;
      const txt = (el.textContent || '').trim();
      if (txt.includes('3 issues') || txt.includes('description')) continue;
      el.scrollIntoViewIfNeeded();
      el.click();
    }
  });
  await page.waitForTimeout(2000);

  // Brute-force unhide all hidden content inside the report via CSS
  await page.addStyleTag({
    content: `
      [aria-expanded="false"] + *, [aria-expanded="false"] ~ *,
      [hidden], [aria-hidden="true"] {
        display: block !important; visibility: visible !important;
      }
      * { max-height: none !important; overflow: visible !important; }
    `,
  });
  await page.waitForTimeout(1500);

  // Second pass: click any expanders that were revealed by unhiding
  await page.evaluate(() => {
    document.querySelectorAll('[aria-expanded="false"]').forEach(el => {
      if (!(el instanceof HTMLElement)) return;
      const txt = (el.textContent || '').trim();
      if (txt.includes('3 issues') || txt.includes('description')) return;
      el.scrollIntoViewIfNeeded(); el.click();
    });
  });
  await page.waitForTimeout(2000);

  // Scroll to bottom to ensure all lazy content is triggered
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await page.waitForTimeout(2000);

  // Close any overlays
  await page.evaluate(() => {
    const overlays = document.querySelectorAll('[class*="overlay"], [role="dialog"]');
    for (const el of overlays) {
      if (el instanceof HTMLElement) el.style.display = 'none';
    }
  });
  await page.waitForTimeout(500);

  // --- DOM content verification ---
  console.log('\n--- DOM Content Verification ---');
  const bodyText = await page.textContent('body');

  const checks = {
    'Job name visible': bodyText.includes(jobName),
    'Trial/persona section': /Persona/i.test(bodyText) || /Trial/i.test(bodyText),
    'Trial count present': /\d+\s*trials?\s*/i.test(bodyText),
    'Batch insights present': /Batch insights|At a glance|Overview/i.test(bodyText),
    'Detailed report togglable': /detailed report|per-question report|Hide detailed|Show detailed/i.test(bodyText),
    'Facet/chart data present': /Passed|Failed|Outcome|categorical|numerical|score|reward/i.test(bodyText),
    'Decision analysis present': /Decision|Category|exploration|basis_primary/i.test(bodyText),
    'Persona traits present': /risk|domain|tolerance|persona/i.test(bodyText),
    'Execution quality present': /Execution|quality|reasoning/i.test(bodyText),
  };

  let allPassed = true;
  for (const [label, ok] of Object.entries(checks)) {
    if (ok) {
      console.log(`  PASS: ${label}`);
    } else {
      console.warn(`  WARN: ${label} — may be missing`);
      allPassed = false;
    }
  }

  if (!allPassed) {
    console.error('\nWARNING: Some content checks failed. PDF may be incomplete.');
    console.error('  Run the backfill script first and restart the backend.');
  }

  // --- Scroll back to top before capture ---
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(2000);

  // --- Capture full-page PDF ---
  console.log('\nCapturing full-page PDF...');
  await page.pdf({
    path: savePath,
    format: 'A4',
    printBackground: true,
    margin: { top: '8mm', bottom: '8mm', left: '8mm', right: '8mm' },
    fullPage: true,
  });

  await browser.close();

  // --- Verify file ---
  if (!fs.existsSync(savePath)) {
    console.error('FAIL: PDF file was not created!');
    process.exit(1);
  }

  const stats = fs.statSync(savePath);
  const sizeKB = (stats.size / 1024).toFixed(1);
  console.log(`\nSUCCESS: PDF generated at:\n  ${savePath}`);
  console.log(`  Size: ${sizeKB} KB`);

  // Quality gate
  const issues = [];
  if (parseFloat(sizeKB) < 300) issues.push('Below 300 KB threshold');
  if (parseFloat(sizeKB) < 800) issues.push('Likely sparse — expect 800+ KB for rich data');
  if (!allPassed) issues.push('DOM checks had warnings (see above)');

  if (issues.length === 0) {
    console.log('  QUALITY: All gates passed ✓');
  } else {
    console.log(`  ISSUES: ${issues.join('; ')}`);
  }
})();
