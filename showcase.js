// Renders the README images: one customer's full set as a strip, and the eight archetype covers.
//   node showcase.js <cid>      (writes docs/cards.png and docs/archetypes.png)
const puppeteer = require("puppeteer");
const fs = require("fs"), path = require("path");
const rows = fs.readFileSync(path.join(__dirname, "out/customers.jsonl"), "utf8").trim().split("\n").map(JSON.parse);
const pick = rows.find((r) => r.cid === process.argv[2]) || rows.sort((a, b) => b.cards.length - a.cards.length)[0];
const covers = []; const seen = new Set();
for (const r of rows) if (!seen.has(r.archetype_key)) { seen.add(r.archetype_key); covers.push(r); }
(async () => {
  const browser = await puppeteer.launch({ headless: "shell", executablePath: process.env.PUPPETEER_EXEC });
  const page = await browser.newPage();
  await page.setViewport({ width: 2400, height: 1200, deviceScaleFactor: 2 });
  await page.goto("file://" + path.join(__dirname, "template.html"), { waitUntil: "networkidle0" });
  await page.evaluate(async () => document.fonts.ready);
  const style = "#stage{gap:16px;padding:16px;background:#fff}";
  await page.addStyleTag({ content: style });
  await page.evaluate(async (c) => { window.renderCards(c); await document.fonts.ready; }, pick);
  await new Promise((r) => setTimeout(r, 500));
  await page.setViewport({ width: (pick.cards.length + 2) * 296 + 16, height: 1200, deviceScaleFactor: 2 });
  await (await page.$("#stage")).screenshot({ path: path.join(__dirname, "docs/cards.png") });
  await page.evaluate((cs) => {
    const html = cs.map((c) => { window.renderCards(c); return document.querySelector("#stage .card").outerHTML; });
    document.getElementById("stage").innerHTML = html.join("");
  }, covers);
  await page.setViewport({ width: 4 * 296 + 16, height: 1200, deviceScaleFactor: 2 });
  await (await page.$("#stage")).screenshot({ path: path.join(__dirname, "docs/archetypes.png") });
  await browser.close();
  console.log("showcase:", pick.cid, pick.first_name, pick.archetype_key);
})();
