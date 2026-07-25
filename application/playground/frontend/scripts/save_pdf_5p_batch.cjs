/**
 * Playwright script: generate PDF for pg-chat-openbb-5p-batch
 * Uses the built-in "Download PDF" button in HarborJobDetail.
 */
const { chromium } = require("playwright");
const path = require("path");
const fs = require("fs");

const BACKEND_URL = "http://127.0.0.1:8767";
const JOB_NAME = "pg-chat-openbb-5p-batch";
const OUTPUT = path.resolve(
  __dirname,
  "..",
  "pg-chat-openbb-5p-batch-persona-task-batch-report.pdf"
);

(async () => {
  console.log("Launching browser...");
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 2,
  });
  const page = await context.newPage();

  const url = `${BACKEND_URL}/?view=runs&harborJob=${JOB_NAME}`;
  console.log(`Navigating to ${url}...`);
  await page.goto(url, { waitUntil: "networkidle", timeout: 60000 });

  // Wait for the job detail to load
  await page.waitForSelector('[data-testid="harbor-job-detail"]', {
    timeout: 30000,
  }).catch(() => console.log("  (no [data-testid] found, continuing)"));

  // Wait for the run detail view
  await page.waitForTimeout(3000);

  // Pre-expand all accordion sections with [aria-expanded="false"]
  console.log("Pre-expanding accordion sections...");
  for (let round = 0; round < 5; round++) {
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
        await page.waitForTimeout(500);
      } catch (e) {
        // element might be stale
      }
    }
    await page.waitForTimeout(2000);
  }

  // Scroll to bottom to trigger any lazy rendering
  console.log("Scrolling to trigger lazy rendering...");
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await page.waitForTimeout(3000);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(2000);

  // Click the Download PDF button
  console.log("Looking for Download PDF button...");
  const downloadBtn = await page.$("text=Download PDF");
  if (!downloadBtn) {
    console.log("  'Download PDF' text not found. Trying button text...");
    const allButtons = await page.$$("button");
    let found = false;
    for (const btn of allButtons) {
      const text = await btn.textContent();
      if (text && text.includes("Download")) {
        console.log(`  Found button with text: "${text.trim()}"`);
        await btn.scrollIntoViewIfNeeded();
        await btn.click();
        found = true;
        break;
      }
    }
    if (!found) {
      console.log("  No Download button found. Saving screenshot for debugging.");
      await page.screenshot({ path: OUTPUT.replace(".pdf", ".png"), fullPage: true });
      console.log(`  Screenshot saved to ${OUTPUT.replace(".pdf", ".png")}`);
      await browser.close();
      process.exit(1);
    }
  } else {
    await downloadBtn.scrollIntoViewIfNeeded();
    await downloadBtn.click();
  }

  // Wait for download to complete
  console.log("Waiting for download...");
  await page.waitForTimeout(5000);

  // Take screenshot as debug
  await page.screenshot({ path: OUTPUT.replace(".pdf", ".png"), fullPage: true });
  console.log(`Screenshot saved to ${OUTPUT.replace(".pdf", ".png")}`);

  // Check if the file was downloaded
  // The browser downloads to default directory; let's check common locations
  const homeDir = require("os").homedir();
  const downloadDirs = [
    path.join(homeDir, "Downloads"),
    path.join(homeDir, "Desktop"),
    __dirname,
  ];
  let foundFile = null;
  for (const dir of downloadDirs) {
    try {
      const files = fs.readdirSync(dir);
      const pdfFile = files.find(
        (f) => f.endsWith(".pdf") && f.includes("persona-task-batch-report")
      );
      if (pdfFile) {
        foundFile = path.join(dir, pdfFile);
        break;
      }
    } catch (e) {
      // skip
    }
  }

  if (foundFile) {
    fs.renameSync(foundFile, OUTPUT);
    console.log(`PDF saved to ${OUTPUT}`);
  } else {
    console.log("PDF not found in expected locations. Trying with download event...");

    // Try again with download event listener
    const download = await new Promise((resolve) => {
      page.on("download", resolve);
      // Click any download-related element
      page.evaluate(() => {
        const btns = document.querySelectorAll("button");
        for (const btn of btns) {
          if (btn.textContent.includes("Download") || btn.textContent.includes("PDF")) {
            btn.click();
            break;
          }
        }
      });
      setTimeout(() => resolve(null), 10000);
    });

    if (download) {
      await download.saveAs(OUTPUT);
      console.log(`PDF saved to ${OUTPUT} (via download event)`);
    } else {
      console.log("Could not capture download. Page might need manual interaction.");
    }
  }

  // Verify file
  try {
    const stat = fs.statSync(OUTPUT);
    console.log(`File size: ${(stat.size / 1024).toFixed(1)} KB`);
    if (stat.size < 300) {
      console.log("WARNING: File size is under 300 KB - may be missing rendered content");
    } else {
      console.log("File size OK (>300 KB)");
    }
  } catch (e) {
    console.log(`Could not verify PDF: ${e.message}`);
  }

  await browser.close();
  console.log("Done.");
})();
