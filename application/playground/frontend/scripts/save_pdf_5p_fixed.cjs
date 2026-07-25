/**
 * Fixed Playwright script: generate PDF for pg-chat-openbb-5p-batch
 * Verifies page content before clicking Download PDF.
 */
const { chromium } = require("playwright");
const path = require("path");
const fs = require("fs");

const BACKEND_URL = "http://127.0.0.1:8767";
const JOB_NAME = "pg-chat-openbb-5p-batch";
const OUTPUT = path.resolve(
  __dirname,
  "..",
  `pg-chat-openbb-5p-batch-persona-task-batch-report-${Date.now()}.pdf`
);

(async () => {
  console.log("Launching browser...");
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 2,
  });
  const page = await context.newPage();

  // Listen for downloads before navigating
  let downloadPromise = null;
  page.on("download", (download) => {
    console.log(`Download started: ${download.suggestedFilename()}`);
    downloadPromise = download;
  });

  const url = `${BACKEND_URL}/?view=runs&harborJob=${JOB_NAME}`;
  console.log(`Navigating to ${url}...`);
  await page.goto(url, { waitUntil: "networkidle", timeout: 60000 });

  // Wait for the page to fully load
  await page.waitForTimeout(5000);

  // Verify we're on the right job by checking page text
  const bodyText = await page.textContent("body");
  if (bodyText.includes("arts-beginner-painting") || bodyText.includes("Arts Beginner")) {
    console.error("ERROR: Page is showing arts-beginner-painting content! Aborting.");
    await page.screenshot({ path: OUTPUT.replace(".pdf", "_error.png"), fullPage: true });
    await browser.close();
    process.exit(1);
  }

  if (!bodyText.includes("Chat Openbb") && !bodyText.includes("chat_openbb") && !bodyText.includes("pg-chat-openbb-5p")) {
    console.warn("WARNING: Could not verify 'Chat Openbb' on page. Text preview:");
    console.warn(bodyText.substring(0, 1000));
  } else {
    console.log("CONFIRMED: Page shows Openbb content.");
  }

  // Pre-expand all accordion sections
  console.log("Pre-expanding accordion sections...");
  for (let round = 0; round < 8; round++) {
    const collapsed = await page.$$('[aria-expanded="false"]');
    if (collapsed.length === 0) {
      console.log(`  All sections expanded after round ${round}`);
      break;
    }
    console.log(`  Round ${round}: expanding ${collapsed.length} sections...`);
    for (const el of collapsed) {
      try {
        await el.scrollIntoViewIfNeeded();
        await el.click();
        await page.waitForTimeout(800);
      } catch (e) {
        // stale element
      }
    }
    await page.waitForTimeout(3000);
  }

  // Scroll to bottom, top, then bottom again for lazy rendering
  console.log("Scrolling for lazy rendering...");
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await page.waitForTimeout(4000);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(4000);
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await page.waitForTimeout(4000);

  // Reset download promise before clicking
  downloadPromise = null;

  // Click the Download PDF button
  console.log("Looking for Download PDF button...");
  const btns = await page.$$("button");
  let clicked = false;
  for (const btn of btns) {
    const text = await btn.textContent();
    if (text && (text.includes("Download") || text.includes("PDF"))) {
      console.log(`  Clicking button: "${text.trim()}"`);
      await btn.scrollIntoViewIfNeeded();
      await btn.click();
      clicked = true;
      break;
    }
  }

  if (!clicked) {
    console.log("  No Download button found. Dumping page HTML snippet...");
    const html = await page.content();
    console.log(html.substring(0, 2000));
    await page.screenshot({ path: OUTPUT.replace(".pdf", "_no_button.png"), fullPage: true });
    await browser.close();
    process.exit(1);
  }

  // Wait for download
  console.log("Waiting for download event...");
  await page.waitForTimeout(3000);

  if (downloadPromise) {
    await downloadPromise.saveAs(OUTPUT);
    console.log(`PDF saved to ${OUTPUT}`);
  } else {
    console.log("No download event captured. Checking common download locations...");
    const homeDir = require("os").homedir();
    const dlDir = path.join(homeDir, "Downloads");
    if (fs.existsSync(dlDir)) {
      const files = fs.readdirSync(dlDir).filter(f => f.endsWith(".pdf"));
      if (files.length > 0) {
        const latest = files
          .map(f => ({ name: f, time: fs.statSync(path.join(dlDir, f)).mtimeMs }))
          .sort((a, b) => b.time - a.time)[0];
        console.log(`  Found recent download: ${latest.name}`);
        fs.copyFileSync(path.join(dlDir, latest.name), OUTPUT);
        console.log(`  Copied to ${OUTPUT}`);
      }
    }
  }

  // Verify the PDF content
  if (fs.existsSync(OUTPUT)) {
    const stat = fs.statSync(OUTPUT);
    console.log(`File size: ${(stat.size / 1024).toFixed(1)} KB`);

    // Check PDF text content to verify it's the right job
    const raw = fs.readFileSync(OUTPUT);
    const text = raw.toString("latin1");
    if (text.includes("arts-beginner-painting")) {
      console.error("ERROR: Generated PDF still contains arts-beginner-painting content!");
      process.exit(1);
    }
    if (text.includes("Openbb") || text.includes("finance") || text.includes("0053") || text.includes("Quant")) {
      console.log("CONFIRMED: PDF contains Openbb/finance content.");
    } else {
      console.warn("WARNING: Could not find Openbb/finance markers in PDF.");
    }
  }

  await browser.close();
  console.log("Done.");
})();
