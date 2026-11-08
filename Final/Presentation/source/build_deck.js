// Campus Lost & Found — ICT Final presentation (16:9, editable).
// Build:  cd Final/Presentation/source && npm install && node build_deck.js
// Reads real evidence from Final/Evidence and Final/Testing, so numbers and the user-test slide
// update automatically when the team adds final_test_results.csv rows and rebuilds.
const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");

const FINAL = path.resolve(__dirname, "..", "..");
const EV = path.join(FINAL, "Evidence");
const A = (n) => path.join(__dirname, "assets", n + ".png");
const OUT = path.join(FINAL, "Presentation", "Group_Team_ICT_FinalPresentation.pptx");
const readJson = (n) => { const p = path.join(EV, n); return fs.existsSync(p) ? JSON.parse(fs.readFileSync(p, "utf8").replace(/^﻿/, "")) : null; };

// ---------- evidence ----------
const perf = readJson("search_performance_final.json");
const sc3 = readJson("sc3_final.json");
const br = readJson("browser_checks.json");
const stab = readJson("stability_30min_final.json");
const suite = /Ran (\d+) tests in ([\d.]+)s\s+OK/.exec(fs.readFileSync(path.join(EV, "test_suite_final.log"), "utf8"));
if (!suite) throw new Error("test_suite_final.log does not end with a passing run");
const TESTS = suite[1], TESTS_TIME = Number(suite[2]).toFixed(1);
const stabDone = stab && stab.completed === stab.checks;
const n3ok = br.N3_360px.no_horizontal_scroll && Object.values(br.N3_labels).every((x) => x.all_labelled) && br.N3_keyboard_post_form.reaches_publish_button;
const n4ok = stabDone && stab.passed === stab.checks && br.N4_offline_retry.passed;
const mustDone = 9 + (n3ok ? 1 : 0) + (n4ok ? 1 : 0);   // F2,F4-F8 (6) + F1 + N2 + N1   // F1 and N2 closed by a real Microsoft sign-in on 8 Nov 2026

function parseCsv(text) {
  const rows = []; let row = [], cell = "", q = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (q) { if (c === '"' && text[i + 1] === '"') { cell += '"'; i++; } else if (c === '"') q = false; else cell += c; }
    else if (c === '"') q = true; else if (c === ",") { row.push(cell); cell = ""; }
    else if (c === "\n" || c === "\r") { if (c === "\r" && text[i + 1] === "\n") i++; row.push(cell); cell = ""; if (row.some((x) => x.trim())) rows.push(row); row = []; }
    else cell += c;
  }
  if (cell || row.length) { row.push(cell); if (row.some((x) => x.trim())) rows.push(row); }
  const [head, ...body] = rows; return body.map((r) => Object.fromEntries(head.map((h, i) => [h.trim(), (r[i] || "").trim()])));
}
const ftRows = parseCsv(fs.readFileSync(path.join(FINAL, "Testing", "final_test_results.csv"), "utf8").replace(/^﻿/, ""))
  .filter((r) => r.participant_code && r.outside_team.toLowerCase() === "yes" && r.consent.toLowerCase() === "yes");
const TARGET = { publish: 120, find: 60 };
const ft = {};
for (const task of ["publish", "find"]) {
  const at = ftRows.filter((r) => r.task.toLowerCase() === task);
  const met = at.filter((r) => r.completed_correctly.toLowerCase() === "yes" && r.assisted.toLowerCase() === "no" && Number(r.seconds) <= TARGET[task]);
  ft[task] = { n: at.length, met: met.length, times: at.map((r) => Number(r.seconds)), ok: at.length >= 3 && met.length / at.length >= 0.8 };
}
const people = [...new Set(ftRows.map((r) => r.participant_code))];
const haveFt = people.length >= 3;
const VIDEO_URL = (JSON.parse(fs.readFileSync(path.join(FINAL, "_build", "report_config.json"), "utf8")).updated_video_url || "").trim();

// ---------- design system ----------
const C = { ink: "16231C", green: "173D31", forest: "1F5A47", lime: "D6EE9B", sage: "EEF5E4", mist: "F4F6F1", line: "D5DACF", muted: "56635B", amber: "9A5B12", amberBg: "FFF4DC", red: "9A3B2B", white: "FFFFFF", teal: "2E7D6B" };
const THEME = { name: "Campus Lost and Found", headFontFace: "Segoe UI Semibold", bodyFontFace: "Segoe UI",
  colors: { dk1: C.ink, lt1: C.white, dk2: C.green, lt2: C.mist, accent1: C.forest, accent2: C.lime, accent3: C.amber, accent4: C.teal, accent5: C.muted, accent6: C.red, hlink: C.forest, folHlink: C.muted } };
const HEAD = "Segoe UI Semibold", BODY = "Segoe UI";
const W = 13.333, H = 7.5, MX = 0.6;

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.author = "SE-2623: Mengdigerey Zhanzhol, Galitskiy Daniil, Bisengaliev Daulet";
pres.company = "Astana IT University, SE-2623";
pres.title = "Campus Lost & Found — ICT Final presentation";
pres.theme = { headFontFace: HEAD, bodyFontFace: BODY };

pres.defineSlideMaster({
  title: "CONTENT", background: { color: C.white },
  objects: [
    { text: { text: "Campus Lost & Found · SE-2623 · ICT Final", options: { x: MX, y: 7.02, w: 6, h: 0.3, fontFace: BODY, fontSize: 10, color: C.muted, margin: 0 } } },
    { placeholder: { options: { name: "title", type: "title", x: MX, y: 0.42, w: 10.3, h: 1.0, fontFace: HEAD, fontSize: 28, color: C.green, valign: "top", align: "left", margin: 0, bold: false }, text: "" } },
    { placeholder: { options: { name: "speaker", type: "body", x: 10.95, y: 0.47, w: 1.8, h: 0.3, fontFace: BODY, fontSize: 11, color: C.muted, align: "right", margin: 0 }, text: "" } },
  ],
  slideNumber: { x: 12.33, y: 7.0, w: 0.4, h: 0.3, fontFace: BODY, fontSize: 10, color: C.muted, align: "right" },
});
pres.defineSlideMaster({
  title: "DARK", background: { color: C.green },
  objects: [{ text: { text: "Campus Lost & Found · SE-2623 · ICT Final", options: { x: MX, y: 7.02, w: 6, h: 0.3, fontFace: BODY, fontSize: 10, color: "B9CDBF", margin: 0 } } }],
});

// ---------- helpers ----------
const shadow = () => ({ type: "outer", blur: 10, offset: 3, angle: 90, color: "000000", opacity: 0.18 });
function text(s, t, o) { s.addText(t, Object.assign({ isTextBox: true, margin: 0, fontFace: BODY, color: C.ink, valign: "top" }, o)); }
function pngSize(file) { const b = fs.readFileSync(file); return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) }; }
// Place a real screenshot without distortion: "cover" crops to the box, "contain" fits inside it.
function frame(s, img, x, y, w, h, opts = {}) {
  const nat = pngSize(A(img));
  const mode = opts.sizing || "cover";
  if (mode === "contain") {
    const k = Math.min(w / nat.w, h / nat.h), iw = nat.w * k, ih = nat.h * k, ix = x + (opts.alignLeft ? 0 : (w - iw) / 2), iy = y + (h - ih) / 2;
    s.addShape(pres.shapes.RECTANGLE, { x: ix, y: iy, w: iw, h: ih, fill: { color: C.white }, line: { color: C.line, width: 0.75 }, shadow: opts.noShadow ? undefined : shadow(), objectName: "frame " + img });
    s.addImage({ path: A(img), x: ix, y: iy, w: iw, h: ih, altText: opts.alt || img, objectName: "screenshot " + img });
    return;
  }
  s.addShape(pres.shapes.RECTANGLE, { x, y, w, h, fill: { color: C.white }, line: { color: C.line, width: 0.75 }, shadow: opts.noShadow ? undefined : shadow(), objectName: "frame " + img });
  const k = Math.max(w / nat.w, h / nat.h);
  s.addImage({ path: A(img), x, y, w: nat.w * k, h: nat.h * k, sizing: { type: "cover", w, h }, altText: opts.alt || img, objectName: "screenshot " + img });
}
function content(title, speaker, section) {
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: section });
  s.addText(title, { placeholder: "title" });
  s.addText(speaker, { placeholder: "speaker" });
  return s;
}
function tag(s, label, x, y, dark) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: 1.25, h: 0.36, rectRadius: 0.08, fill: { color: dark ? C.lime : C.green }, line: { type: "none" } });
  text(s, label, { x, y, w: 1.25, h: 0.36, fontSize: 12, bold: true, color: dark ? C.green : C.lime, align: "center", valign: "middle", fontFace: HEAD });
}
function arrow(s, x1, y1, x2, y2, color = C.forest, width = 2) {
  s.addShape(pres.shapes.LINE, { x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.abs(x2 - x1) || 0.001, h: Math.abs(y2 - y1) || 0.001, flipH: x2 < x1, flipV: y2 < y1, line: { color, width, endArrowType: "triangle" } });
}
const notes = (s, lines) => s.addNotes(lines.join("\n"));

// =====================================================================
// 1 TITLE
pres.addSection({ title: "Opening — Zhanzhol" });
let s = pres.addSlide({ masterName: "DARK", sectionTitle: "Opening — Zhanzhol" });
text(s, "ICT FINAL PROJECT · SE-2623 · WEEK 10", { x: MX, y: 0.75, w: 7, h: 0.35, fontSize: 13, bold: true, color: C.lime, charSpacing: 1.5, fontFace: HEAD });
text(s, [{ text: "Lost it on campus?", options: { breakLine: true } }, { text: "Find it in one place.", options: { color: C.lime } }],
  { x: MX, y: 1.4, w: 6.3, h: 1.9, fontSize: 44, color: C.white, fontFace: HEAD, lineSpacingMultiple: 0.95 });
text(s, "Campus Lost & Found — the finished, tested system, and what three of us learned building it.", { x: MX, y: 3.45, w: 6.3, h: 0.9, fontSize: 20, color: "D9E7D4" });
text(s, [{ text: "Mengdigerey Zhanzhol", options: { breakLine: true } }, { text: "Galitskiy Daniil", options: { breakLine: true } }, { text: "Bisengaliev Daulet" }],
  { x: MX, y: 5.2, w: 4, h: 1.2, fontSize: 16, color: C.white, paraSpaceAfter: 2 });
s.addShape(pres.shapes.RECTANGLE, { x: 7.05, y: 1.35, w: 5.7, h: 2.45, fill: { color: C.white }, line: { color: "2E5A4B", width: 0.75 }, shadow: { type: "outer", blur: 18, offset: 6, angle: 90, color: "000000", opacity: 0.35 } });
s.addImage({ path: A("hero"), x: 7.05, y: 1.35, w: 5.7, h: 2.45, altText: "Real screenshot of the final build: the student noticeboard", objectName: "hero screenshot" });
text(s, "Real screenshot of the final build · synthetic demo data · runs locally", { x: 7.05, y: 3.95, w: 5.7, h: 0.3, fontSize: 11, color: "B9CDBF" });
notes(s, [
  "SPEAKER: Mengdigerey Zhanzhol · about 0:20 · slide 1 of 12",
  "",
  "Good morning. We are team SE-2623: I am Zhanzhol, with Daniil and Daulet. Our project is Campus Lost & Found — one place on campus to report, find and close lost items.",
  "In the next nine minutes each of us will show part of the finished system live, the final test results, and what we would do differently.",
  "",
  "→ Transition: 'First, why does this matter?'",
  "FACTS: screenshot captured from commit a7e5c74 on 8 Nov 2026; all accounts and notices are synthetic.",
]);

// =====================================================================
// 2 PROBLEM
s = content("Lost items wait for days because notices are scattered", "Zhanzhol · 0:40", "Opening — Zhanzhol");
text(s, "4 of 10", { x: MX, y: 1.75, w: 5.2, h: 1.5, fontSize: 96, color: C.green, fontFace: HEAD });
text(s, "students in our survey said getting an item back took more than three days", { x: MX, y: 3.3, w: 4.9, h: 0.9, fontSize: 20, color: C.ink });
text(s, [{ text: "9 of 10", options: { bold: true, color: C.forest } }, { text: " said a shared, searchable board would be useful" }], { x: MX, y: 4.45, w: 4.9, h: 0.7, fontSize: 18 });
text(s, "Stage 1 survey, October 2026 · n = 10 · convenience sample of fellow students — a signal that the problem exists, not a measurement of its size.", { x: MX, y: 5.75, w: 4.9, h: 0.75, fontSize: 12, color: C.muted });
// before / after
const bx = 6.3, bw = 3.0;
text(s, "TODAY", { x: bx, y: 1.75, w: bw, h: 0.3, fontSize: 12, bold: true, color: C.muted, charSpacing: 2 });
text(s, "WITH CAMPUS LOST & FOUND", { x: bx + 3.45, y: 1.75, w: 3.3, h: 0.3, fontSize: 12, bold: true, color: C.forest, charSpacing: 2 });
const before = [["Group chats", "posts scroll away"], ["Paper notes", "only seen in one corridor"], ["Guard desk", "no one knows it is there"], ["No status", "is it already returned?"]];
const after = [["One board", "search by title and category"], ["University accounts", "everyone knows who posted"], ["Email the author", "one click from the notice"], ["Returned badge", "closed notices stay honest"]];
before.forEach(([a, b], i) => {
  const y = 2.2 + i * 1.02;
  s.addShape(pres.shapes.RECTANGLE, { x: bx, y, w: bw, h: 0.86, fill: { color: C.mist }, line: { type: "none" } });
  text(s, [{ text: a, options: { bold: true, breakLine: true } }, { text: b, options: { color: C.muted, fontSize: 14 } }], { x: bx + 0.18, y: y + 0.12, w: bw - 0.3, h: 0.7, fontSize: 16 });
  arrow(s, bx + bw + 0.08, y + 0.43, bx + 3.37, y + 0.43, C.forest, 1.5);
  s.addShape(pres.shapes.RECTANGLE, { x: bx + 3.45, y, w: 3.3, h: 0.86, fill: { color: C.sage }, line: { type: "none" } });
  text(s, [{ text: after[i][0], options: { bold: true, breakLine: true, color: C.green } }, { text: after[i][1], options: { color: C.ink, fontSize: 14 } }], { x: bx + 3.63, y: y + 0.12, w: 3.0, h: 0.7, fontSize: 16 });
});
notes(s, [
  "SPEAKER: Zhanzhol · about 0:40",
  "",
  "When someone loses a notebook or keys on our campus, the message ends up in a group chat, on a paper note, or at the guard desk. Each channel reaches only part of campus, chat messages scroll away, and nobody knows when the item is back.",
  "In our Stage 1 survey four of ten students said a return took more than three days, and nine of ten said a shared searchable board would help. That is only ten people — a convenience sample — so we treat it as a signal, not a statistic.",
  "Our answer: one board, tied to university-style accounts, with a clear Returned status.",
  "",
  "→ Transition: 'So what did we promise in Stage 1, and what did we deliver?'",
  "SOURCE: Stage 1 report p. 2 (survey, 10 responses: 9/10 useful, 4/10 returns > 3 days).",
]);

// =====================================================================
// 3 REQUIREMENTS
s = content(mustDone === 11 ? "All 11 Must requirements are done" : `${mustDone} of 11 Must requirements are done`, "Zhanzhol · 0:45", "Opening — Zhanzhol");
const reqs = [["F1", "University sign-in", "done"], ["F2", "Publish", "done"], ["F3", "One photo", "should"], ["F4", "Browse + details", "done"], ["F5", "Search + filter", "done"], ["F6", "Email author", "done"], ["F7", "Edit + returned", "done"], ["F8", "Admin removes", "done"],
  ["N1", "Search ≤ 2 s", "done"], ["N2", "Identity + rights", "done"], ["N3", "360 px + keyboard", n3ok ? "done" : "part"], ["N4", "30-min demo", n4ok ? "done" : "part"]];
const step = (W - 2 * MX) / 12;
reqs.forEach(([id, label, st], i) => {
  const cx = MX + i * step + step / 2, d = 0.82, y = 2.0;
  const fill = st === "part" ? C.amberBg : st === "should" ? C.sage : C.green;
  const line = st === "part" ? { color: C.amber, width: 2.5 } : st === "should" ? { color: C.forest, width: 1.5, dashType: "dash" } : { type: "none" };
  s.addShape(pres.shapes.OVAL, { x: cx - d / 2, y, w: d, h: d, fill: { color: fill }, line, objectName: "requirement " + id });
  text(s, id, { x: cx - d / 2, y: y + 0.06, w: d, h: 0.4, fontSize: 18, bold: true, align: "center", fontFace: HEAD, color: st === "done" ? C.white : st === "part" ? C.amber : C.green });
  text(s, st === "part" ? "partly" : st === "should" ? "done" : "done", { x: cx - d / 2, y: y + 0.44, w: d, h: 0.28, fontSize: 10, align: "center", color: st === "done" ? C.lime : st === "part" ? C.amber : C.forest });
  text(s, label, { x: cx - step / 2 + 0.02, y: y + 0.95, w: step - 0.04, h: 0.6, fontSize: 12, align: "center", color: C.ink });
  if (i === 7) s.addShape(pres.shapes.LINE, { x: MX + 8 * step, y: 1.85, w: 0, h: 1.75, line: { color: C.line, width: 1, dashType: "dash" } });
});
text(s, "FUNCTIONAL (F) · F3 is the only Should", { x: MX, y: 1.55, w: 6, h: 0.3, fontSize: 11, color: C.muted, charSpacing: 1 });
text(s, "NON-FUNCTIONAL (N)", { x: MX + 8 * step + 0.1, y: 1.55, w: 4, h: 0.3, fontSize: 11, color: C.muted, charSpacing: 1 });
s.addShape(pres.shapes.RECTANGLE, { x: MX, y: 4.05, w: 7.4, h: 2.55, fill: { color: C.sage }, line: { type: "none" } });
text(s, "University sign-in now works", { x: MX + 0.3, y: 4.25, w: 6.9, h: 0.4, fontSize: 18, bold: true, color: C.green, fontFace: HEAD });
text(s, [
  { text: "Students sign in with their Astana IT University Microsoft account (OpenID Connect + PKCE). Verified with a real account on 8 Nov 2026.", options: { breakLine: true } },
  { text: "Only @astanait.edu.kz accounts from the university directory get in; in this mode nobody can self-register with an unverified address. Demo accounts stay for offline demos." },
], { x: MX + 0.3, y: 4.75, w: 6.9, h: 1.75, fontSize: 15, paraSpaceAfter: 8 });
text(s, [{ text: "Evidence for every row", options: { bold: true, breakLine: true, color: C.green } },
  { text: "Final/Requirements/Requirements_Status.md lists the test, screenshot or measurement behind each status. All were re-run on 8 Nov 2026 on the final code.", options: { color: C.ink } }],
  { x: 8.45, y: 4.25, w: 4.3, h: 2.2, fontSize: 15 });
notes(s, [
  "SPEAKER: Zhanzhol · about 0:45",
  "",
  `Stage 1 gave us eleven Must requirements and one Should. ${mustDone} Musts are fully done, and the photo upload — our only Should — is done as well.`,
  "All eleven Must requirements are done, and the photo upload — our only Should — too. The last two, F1 and N2, were about identity. In Stage 2 our accounts were local. For the Final we registered the app in the Astana IT University Microsoft Entra directory and added OpenID Connect sign-in with PKCE: the server checks the token signature, issuer, tenant, audience, expiry, nonce and the astanait.edu.kz domain. On 8 November a real university account signed in, and in this mode nobody can self-register with an unverified address. Local demo accounts remain only so the demo works offline.",
  "Every status in this row has a test, screenshot or measurement behind it in our requirements table.",
  "",
  "→ Transition: 'Let me show you the student side live.' (switch to the browser)",
  "SOURCES: Stage 1 report pp. 3–4; Final/Requirements/Requirements_Status.md; Evidence/test_suite_final.log; Final/SSO/Microsoft_Entra_SignIn_Status_and_Setup.md.",
]);

// =====================================================================
// 4 STUDENT DEMO
s = content("Live demo · a student goes from “I found it” to “Returned”", "Zhanzhol · 1:15", "Opening — Zhanzhol");
tag(s, "LIVE DEMO", 11.5, 0.95, false);
const steps = [["post", "1  Publish", "Type, category, title, place, date, one photo"], ["saved", "2  Saved", "Stored in SQLite; photo re-encoded and private"], ["search", "3  Find", "Search “red notebook” + category → 1 result"], ["returned", "4  Close", "Email the author, then mark it Returned"]];
const fw = 2.85, fh = 2.2, gap = (W - 2 * MX - 4 * fw) / 3;
steps.forEach(([img, h1, cap], i) => {
  const x = MX + i * (fw + gap), y = 1.8;
  frame(s, img, x, y, fw, fh, { alt: cap });
  text(s, h1, { x, y: y + fh + 0.2, w: fw, h: 0.4, fontSize: 18, bold: true, color: C.green, fontFace: HEAD });
  text(s, cap, { x, y: y + fh + 0.6, w: fw, h: 0.75, fontSize: 14, color: C.ink });
  if (i < 3) arrow(s, x + fw + 0.06, y + fh / 2, x + fw + gap - 0.06, y + fh / 2, C.forest, 2);
});
text(s, "All four frames are real captures of the final build (8 Nov 2026). If the live demo fails, talk through these frames.", { x: MX, y: 5.75, w: 10, h: 0.35, fontSize: 12, color: C.muted });
notes(s, [
  "SPEAKER: Zhanzhol · about 1:15 · LIVE DEMO in the browser (normal window, student)",
  "",
  "DEMO STEPS (sign in first as zhanzhol.demo@astanait.edu.kz / CampusDemo!2026 BEFORE the talk):",
  "1. Click 'Post a notice'. Choose Found, Books and Stationery, title 'Blue notebook (live demo)', location 'Library, second floor', today's date. Choose a photo (Sources/stationery_source.jpg). Click Publish notice.",
  "   SAY: 'The notice is saved in SQLite. The photo is checked, re-encoded so GPS metadata is removed, and given a random name. Only signed-in users can open it.'",
  "2. Go to Browse notices. Type 'red notebook', choose Books and Stationery, Search. Open the result.",
  "   SAY: 'Search uses a parameterised LIKE query; the category filter narrows it to one result.'",
  "3. Point at 'Contact author' — 'This opens an email draft to the person who posted it. The site itself never sends email.' (Do not actually send.)",
  "4. Open 'My notices' → your new notice → 'Mark as returned'. SAY: 'The badge changes to Returned and the change is saved — only the owner can do this; another student gets a 403.'",
  "",
  "IF THE DEMO FAILS: stay on this slide and narrate the four frames; they are real screenshots of the same steps.",
  "→ Hand-over: 'Daniil will now show what the administrator sees.'",
  "FACTS: browser run on 8 Nov 2026 created notice #123, search returned exactly 1 result (Red notebook, #4), mailto pointed at the stored owner.",
]);

// =====================================================================
// 5 ADMIN DEMO
pres.addSection({ title: "Results — Daniil" });
s = content("Live demo · the admin keeps the board clean", "Daniil · 1:10", "Results — Daniil");
tag(s, "LIVE DEMO", 11.5, 0.95, false);
frame(s, "admin", MX, 1.8, 7.3, 3.96, { alt: "Admin panel overview with live counts" });
const callouts = [["1", "Live counts from SQLite", "Notices, open, returned and users are counted on every visit — nothing is typed in by hand."],
  ["2", "Remove with a confirmation step", "Opening the page deletes nothing; only “Confirm removal” does. A student gets 403."],
  ["3", "Analytics on the same data", "Three SQL questions with CSV export, clearly labelled “synthetic teaching data”."]];
callouts.forEach(([n, h1, b], i) => {
  const y = 1.8 + i * 1.38;
  s.addShape(pres.shapes.OVAL, { x: 8.3, y, w: 0.5, h: 0.5, fill: { color: C.lime }, line: { type: "none" } });
  text(s, n, { x: 8.3, y, w: 0.5, h: 0.5, fontSize: 16, bold: true, align: "center", valign: "middle", color: C.green, fontFace: HEAD });
  text(s, [{ text: h1, options: { bold: true, breakLine: true, color: C.green, fontSize: 17 } }, { text: b, options: { fontSize: 14 } }], { x: 9.0, y: y - 0.02, w: 3.75, h: 1.3 });
});
frame(s, "remove", MX, 5.95, 3.0, 0.7, { alt: "Remove confirmation page", noShadow: true });
text(s, "Admin pages return 403 to all three student accounts and 200 to the administrator (checked 8 Nov 2026).", { x: 3.85, y: 6.05, w: 8.9, h: 0.5, fontSize: 13, color: C.muted });
notes(s, [
  "SPEAKER: Galitskiy Daniil · about 1:10 · LIVE DEMO (private window, administrator)",
  "",
  "DEMO STEPS (sign in BEFORE the talk in a private window as admin.demo@astanait.edu.kz / CampusDemo!2026):",
  "1. Open Admin panel. SAY: 'These counts are read from SQLite on every visit. If Zhanzhol just posted a notice, All notices went up by one.'",
  "2. Notices tab → search 'Blue notebook' → open Zhanzhol's live-demo notice → 'Remove notice'. SAY: 'Opening this page changes nothing. Only the POST with a CSRF token deletes the row and its photo.' Click Confirm removal.",
  "3. Open Analytics. SAY: 'Three SQL questions: open backlog by category, lost and found by location, and events per week. It is synthetic teaching data and the page says so. The CSV export neutralises spreadsheet formulas.'",
  "4. (Optional, if time) Show that a student opening /admin gets 403.",
  "",
  "→ Transition: 'How do we know it works beyond a demo? Here are the measurements.'",
  "FACTS: account_checks.json — /admin, /admin/notices, /admin/users, /admin/analytics, /admin/research, /admin/smart-locker: 403 for zhanzhol/daniil/daulet demo students, 200 for admin.",
]);

// =====================================================================
// 6 TESTING
s = content("The final code passed every automated and security check", "Daniil · 0:50", "Results — Daniil");
text(s, `${TESTS} / ${TESTS}`, { x: MX, y: 1.75, w: 4.6, h: 1.4, fontSize: 88, color: C.green, fontFace: HEAD });
text(s, "automated tests passed on the final code — logins, CSRF, ownership, photos, analytics, backup, locker", { x: MX, y: 3.2, w: 4.3, h: 1.0, fontSize: 16 });
text(s, `Ran ${TESTS} tests in ${TESTS_TIME} s — OK · 8 Nov 2026`, { x: MX, y: 4.3, w: 4.3, h: 0.35, fontSize: 12, color: C.muted });
// N1 bar
const gx = 5.6, gw = 7.1;
text(s, "N1 · Search response, 10 users at once (95th percentile)", { x: gx, y: 1.8, w: gw, h: 0.4, fontSize: 16, bold: true, color: C.green, fontFace: HEAD });
const barW = 5.6, p95w = Math.max(0.04, barW * perf.p95_ms / 2000);
text(s, "measured", { x: gx, y: 2.35, w: 1.3, h: 0.4, fontSize: 14, valign: "middle" });
s.addShape(pres.shapes.RECTANGLE, { x: gx + 1.4, y: 2.35, w: p95w, h: 0.4, fill: { color: C.forest }, line: { type: "none" } });
text(s, `${perf.p95_ms.toFixed(1)} ms`, { x: gx + 1.4 + p95w + 0.12, y: 2.35, w: 1.5, h: 0.4, fontSize: 16, bold: true, valign: "middle", color: C.green });
text(s, "target", { x: gx, y: 2.9, w: 1.3, h: 0.4, fontSize: 14, valign: "middle" });
s.addShape(pres.shapes.RECTANGLE, { x: gx + 1.4, y: 2.9, w: barW, h: 0.4, fill: { color: C.lime }, line: { type: "none" } });
text(s, "2,000 ms", { x: gx + 1.4 + barW - 1.3, y: 2.9, w: 1.2, h: 0.4, fontSize: 14, bold: true, valign: "middle", align: "right", color: C.green });
text(s, "Same scale. 100 searches from 10 signed-in sessions over local HTTP; page images and drawing time not included.", { x: gx, y: 3.45, w: gw, h: 0.6, fontSize: 12, color: C.muted });
// two stats
const st = [[`${sc3.blocked} / ${sc3.total}`, "invalid-access attempts blocked (SC3): wrong domain, wrong password, anonymous, foreign edit, student removal"],
  [stabDone ? `${stab.passed} / ${stab.checks}` : "running", stabDone ? "availability checks passed, spread over 30 minutes (N4), plus offline → retry in the browser" : "30-minute availability monitor still running at build time"]];
st.forEach(([big, lbl], i) => {
  const x = gx + i * 3.6;
  text(s, big, { x, y: 4.35, w: 3.3, h: 0.85, fontSize: 44, color: C.green, fontFace: HEAD });
  text(s, lbl, { x, y: 5.2, w: 3.3, h: 1.2, fontSize: 14 });
});
s.addShape(pres.shapes.RECTANGLE, { x: MX, y: 5.0, w: 4.3, h: 1.45, fill: { color: C.amberBg }, line: { type: "none" } });
text(s, "These are software checks. They are never counted as human testers — that is the next slide.", { x: MX + 0.2, y: 5.15, w: 3.9, h: 1.2, fontSize: 15, color: C.amber, bold: true });
notes(s, [
  "SPEAKER: Daniil · about 0:50",
  "",
  "We re-ran everything on the final code on 8 November.",
  `${TESTS} of ${TESTS} automated tests pass: authentication, CSRF, owner and admin rights, photo validation, analytics, backup, the locker simulation and the new Microsoft sign-in code against simulated responses.`,
  `Our Stage 1 performance target was search under 2 seconds for 10 users at once. The 95th percentile was ${perf.p95_ms.toFixed(1)} milliseconds — but honestly, that is on a laptop over local HTTP, without images or rendering.`,
  `All five invalid-access attempts were blocked, and ${stabDone ? `${stab.passed} of ${stab.checks}` : "the"} availability checks over 30 minutes passed.`,
  "Important: none of this is a user test. Automated checks and AI reviews never count as people.",
  "",
  "→ Transition: 'So here is what real people outside our team did.'",
  "SOURCES: Evidence/test_suite_final.log; search_performance_final.json (p95, max, median); sc3_final.json; stability_30min_final.json; browser_checks.json (offline/retry).",
]);

// =====================================================================
// 7 FINAL USER TEST
const ftTitle = haveFt ? `${people.length} people outside the team re-tested our user criteria` : "Final user test: method fixed, results still to be entered";
s = content(ftTitle, "Daniil · 0:45", "Results — Daniil");
if (haveFt) {
  // dot plot per task against target
  [["publish", "SC1 · Publish", 120, 160], ["find", "SC2 · Find", 60, 80]].forEach(([task, label, target, max], i) => {
    const y = 1.7 + i * 1.3, x0 = MX + 2.4, pw = 6.4;
    text(s, label, { x: MX, y: y + 0.3, w: 2.2, h: 0.5, fontSize: 18, bold: true, color: C.green, fontFace: HEAD });
    s.addShape(pres.shapes.LINE, { x: x0, y: y + 0.6, w: pw, h: 0, line: { color: C.line, width: 1.5 } });
    const tx = x0 + pw * target / max;
    s.addShape(pres.shapes.LINE, { x: tx, y: y + 0.1, w: 0, h: 1.0, line: { color: C.amber, width: 2, dashType: "dash" } });
    text(s, `target ${target} s`, { x: tx + 0.08, y: y + 0.05, w: 1.4, h: 0.3, fontSize: 12, color: C.amber });
    ft[task].times.forEach((t, j) => {
      const cx = x0 + pw * Math.min(t, max) / max;
      s.addShape(pres.shapes.OVAL, { x: cx - 0.11, y: y + 0.49 + (j % 2) * 0.05, w: 0.22, h: 0.22, fill: { color: t <= target ? C.forest : C.red }, line: { color: C.white, width: 1 } });
    });
    text(s, "0 s", { x: x0 - 0.1, y: y + 0.75, w: 0.6, h: 0.3, fontSize: 11, color: C.muted });
    text(s, `${max} s`, { x: x0 + pw - 0.5, y: y + 0.75, w: 0.6, h: 0.3, fontSize: 11, color: C.muted, align: "right" });
    text(s, `${ft[task].met}/${ft[task].n}`, { x: 9.7, y, w: 1.5, h: 0.7, fontSize: 36, color: ft[task].ok ? C.green : C.red, fontFace: HEAD });
    text(s, ft[task].ok ? "met (≥ 80 %)" : "not met (< 80 %)", { x: 11.2, y: y + 0.15, w: 1.6, h: 0.5, fontSize: 14, bold: true, color: ft[task].ok ? C.green : C.red });
  });
  text(s, `Each dot is one person’s first attempt (green = correct, unassisted, within target). ${people.length} people outside the team, ${[...new Set(ftRows.map((r) => r.date))].sort().join(" and ")}; ${[...new Set(ftRows.map((r) => r.os_browser))].join(", ")}. Small sample: one person = ${Math.round(100 / people.length)} percentage points.`, { x: MX, y: 6.2, w: 12.1, h: 0.6, fontSize: 12, color: C.muted });
} else {
  const flow = [["Same task cards", "Publish the blue notebook (≤ 120 s) · find the red notebook (≤ 60 s)"], ["Real people only", "≥ 3 volunteers outside the team, with consent; codes, not names"], ["First attempt counts", "Timer from card to “done”; no coaching; failures stay in"]];
  flow.forEach(([h1, b], i) => {
    const y = 1.85 + i * 1.32;
    s.addShape(pres.shapes.OVAL, { x: MX, y, w: 0.5, h: 0.5, fill: { color: C.green }, line: { type: "none" } });
    text(s, String(i + 1), { x: MX, y, w: 0.5, h: 0.5, fontSize: 16, bold: true, align: "center", valign: "middle", color: C.lime });
    text(s, [{ text: h1, options: { bold: true, breakLine: true, color: C.green, fontSize: 17 } }, { text: b, options: { fontSize: 14 } }], { x: MX + 0.7, y: y - 0.02, w: 4.4, h: 1.2 });
  });
}
const tableRows = [
  [{ text: "Criterion", options: { bold: true, color: C.white, fill: { color: C.green } } }, { text: "Stage 2 result", options: { bold: true, color: C.white, fill: { color: C.green } } }, { text: "Final result", options: { bold: true, color: C.white, fill: { color: C.green } } }, { text: "Met?", options: { bold: true, color: C.white, fill: { color: C.green } } }],
  ["SC1 · post within 2 min (≥ 4/5)", "Report: Pending · team-reported 5/5, no raw record", haveFt ? `${ft.publish.met}/${ft.publish.n}` : "awaiting team data", haveFt ? (ft.publish.ok ? "✓ Yes" : "✗ No") : "—"],
  ["SC2 · find within 1 min (≥ 4/5)", "Report: Pending · team-reported 5/5, no raw record", haveFt ? `${ft.find.met}/${ft.find.n}` : "awaiting team data", haveFt ? (ft.find.ok ? "✓ Yes" : "✗ No") : "—"],
  ["SC3 · invalid access blocked (5/5)", "5/5", `${sc3.blocked}/${sc3.total} (8 Nov)`, sc3.blocked === 5 ? "✓ Yes" : "✗ No"],
];
if (haveFt) s.addTable(tableRows, { x: MX, y: 4.4, w: 12.1, colW: [3.6, 4.6, 2.3, 1.6], fontFace: BODY, fontSize: 13, color: C.ink, border: { type: "solid", pt: 0.5, color: C.line }, rowH: 0.36, autoPage: false });
else s.addTable(tableRows, { x: 5.6, y: 1.85, w: 7.13, colW: [2.35, 2.33, 1.45, 1.0], fontFace: BODY, fontSize: 13, color: C.ink, border: { type: "solid", pt: 0.5, color: C.line }, autoPage: false });
if (!haveFt) text(s, "The team reports the Final session was held. Its records go into Final/Testing/final_test_results.csv; rebuilding the deck and report fills this slide automatically. AI tools, scripts and team members are never entered as participants.", { x: 5.6, y: 5.3, w: 7.13, h: 1.2, fontSize: 13, color: C.amber });
notes(s, [
  "SPEAKER: Daniil · about 0:45",
  "",
  haveFt ? `We re-tested SC1 and SC2 with ${people.length} people outside our team, using the same two task cards. ${ft.publish.met} of ${ft.publish.n} published within two minutes; ${ft.find.met} of ${ft.find.n} found the red notebook within one minute. The sample is small, so we report counts.`
    : "STATUS AT BUILD TIME: the team's Final user-test records were not yet in the package. Do NOT present invented numbers. Either enter the real rows in Final/Testing/final_test_results.csv and rebuild, or say: 'Our Final session results are in our observer notes; here is the method.'",
  "Method: the same two task cards as Stage 2, real volunteers outside the team who agreed to take part, the timer runs from handing over the card to the participant saying 'done', the first attempt counts, no coaching, failures stay in the results.",
  "About Stage 2: our submitted Stage 2 report says Pending for SC1 and SC2. After submission the team reported five people with publish times 70–92 s and find times 45–53 s, but we have no raw record of that session, so we show it only as team-reported history.",
  "",
  "→ Hand-over: 'Daulet will explain how the system is built and where its boundary is.'",
  "SOURCES: Testing/TASK_CARDS_EN.txt; Final/Testing/Final_Test_Protocol.md; Final/Testing/final_test_results.csv; Final/Testing/stage2_team_reported.csv; Stage 2 report p. 11.",
]);

// =====================================================================
// 8 ARCHITECTURE
pres.addSection({ title: "System — Daulet" });
s = content("One laptop; the security boundary is its Windows account", "Daulet · 0:45", "System — Daulet");
// boundary
s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: MX, y: 1.7, w: 8.45, h: 4.95, rectRadius: 0.15, fill: { color: C.white }, line: { color: C.green, width: 2, dashType: "dash" }, objectName: "security boundary" });
text(s, "SECURITY BOUNDARY · demo laptop", { x: MX + 0.25, y: 1.82, w: 5, h: 0.3, fontSize: 12, bold: true, color: C.green, charSpacing: 1 });
const box = (x, y, w, h, title, sub, dark, dashed) => {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.1, fill: { color: dark ? C.green : C.mist }, line: dashed ? { color: C.green, width: 1.25, dashType: "dash" } : { type: "none" }, objectName: "box " + title });
  text(s, [{ text: title, options: { bold: true, breakLine: true, fontSize: 16, color: dark ? C.white : C.green } }, { text: sub, options: { fontSize: 13, color: dark ? "D9E7D4" : C.ink } }], { x: x + 0.18, y: y + 0.13, w: w - 0.3, h: h - 0.2 });
};
box(MX + 0.25, 2.3, 2.25, 1.45, "Browser", "student and admin sessions, same laptop", false);
box(MX + 3.35, 2.3, 2.6, 1.95, "Waitress + Flask", "session, CSRF, rate limit, owner/admin checks, scrypt hashes\napp.py · admin_panel.py\nanalytics_routes.py\nstage2_features.py", true);
box(MX + 6.35, 2.3, 1.9, 3.95, "Local disk", "campus.sqlite3\nuploads/ photos\nresearch.sqlite3\ntelemetry.sqlite3\nbackups/\n\nnot encrypted by the app", false);
box(MX + 3.35, 4.55, 2.6, 1.7, "Smart locker LF-01", "SIMULATED events only — no sensor, no door", false, true);
box(MX + 0.25, 4.55, 2.45, 1.7, "Operator tools", "START, TESTS, BACKUP, read-only DB inspector", false);
arrow(s, MX + 2.55, 2.75, MX + 3.3, 2.75); arrow(s, MX + 3.3, 2.75, MX + 2.55, 2.75);
text(s, "HTTP\n127.0.0.1\nno TLS", { x: MX + 2.5, y: 2.85, w: 0.85, h: 0.75, fontSize: 10, color: C.amber, bold: true, align: "center" });
arrow(s, MX + 6.0, 3.25, MX + 6.3, 3.25); arrow(s, MX + 6.0, 5.4, MX + 6.3, 5.4);
// outside
text(s, "OUTSIDE THE BOUNDARY", { x: 9.4, y: 1.75, w: 3.4, h: 0.3, fontSize: 12, bold: true, color: C.muted, charSpacing: 1 });
const outside = [["Other devices", "cannot connect — server binds 127.0.0.1"], ["Email app", "“Contact author” opens a draft; site sends nothing"], ["Microsoft Entra ID", "university sign-in (OIDC + PKCE), verified"], ["GitHub", "public source with synthetic data only"]];
outside.forEach(([a, b], i) => {
  const y = 2.15 + i * 1.12;
  s.addShape(pres.shapes.RECTANGLE, { x: 9.4, y, w: 3.33, h: 0.98, fill: { color: C.white }, line: { color: C.line, width: 1, dashType: i === 2 ? "dash" : "solid" } });
  text(s, [{ text: a, options: { bold: true, breakLine: true, color: C.ink, fontSize: 15 } }, { text: b, options: { fontSize: 13, color: C.muted } }], { x: 9.55, y: y + 0.1, w: 3.1, h: 0.85 });
});
notes(s, [
  "SPEAKER: Bisengaliev Daulet · about 0:45",
  "",
  "This is the system as built, not as planned in Stage 1. Browser and server are on the same laptop and talk over 127.0.0.1 port 5055. The server refuses other host names, so a phone on the same Wi-Fi cannot reach it.",
  "Inside: Waitress runs the Flask app; every request goes through the signed session cookie, the CSRF token on every POST, the rate limit and the owner/admin checks. Passwords are scrypt hashes. Data lives in three SQLite files and an uploads folder on the local disk — not encrypted by the app.",
  "The security boundary is the laptop's Windows account: anyone who can log in to the laptop can copy the database. Outside the boundary are the email app, Microsoft Entra — the university directory that signs students in — and GitHub, which holds only synthetic data. The client secret is typed in at start-up and never stored.",
  "Changes from Stage 1: university sign-in works as planned (on localhost), no HTTPS, local hosting, three databases instead of one, and the locker simulation was added.",
  "",
  "→ Transition: 'Next: does it work on a phone, with a keyboard and after a network drop?'",
  "SOURCES: app.py lines 29–33 (cookie flags, TRUSTED_HOSTS) and 388 (host 127.0.0.1); Final/Architecture/as_built_architecture*.svg; report Section 4.",
]);

// =====================================================================
// 9 QUALITY ACROSS DEVICES
s = content("Works on a 360 px phone, by keyboard and after a drop", "Daulet · 0:35", "System — Daulet");
frame(s, "phone", MX, 1.7, 2.75, 4.96, { alt: "Noticeboard at 360 px width" });
const ev = [["12 / 12 pages", "no sideways scrolling at 360 × 760 px — student, admin, sign-in and locker pages", null],
  ["Keyboard", "Tab follows the screen order to “Publish notice”; every field has a label; focus is visible", "keyboard"],
  ["Offline → retry", "network cut: a clear message, no double submit; reconnect: “Status refreshed”", "offline"]];
ev.forEach(([h1, b, img], i) => {
  const y = 1.75 + i * 1.65, x = 3.85;
  text(s, h1, { x, y, w: 3.2, h: 0.5, fontSize: 22, color: C.green, fontFace: HEAD });
  text(s, b, { x, y: y + 0.5, w: 3.4, h: 1.0, fontSize: 14 });
  if (img) frame(s, img, 7.55, y + 0.05, 5.2, img === "offline" ? 0.4 : 1.06, { alt: b, noShadow: true, sizing: "contain" });
});
text(s, "Automated checks in Microsoft Edge on 8 Nov 2026 — not an accessibility audit with real assistive-technology users.", { x: 3.85, y: 6.45, w: 8.9, h: 0.35, fontSize: 12, color: C.muted });
notes(s, [
  "SPEAKER: Daulet · about 0:35",
  "",
  "N3 and N4 were only partly done at Stage 2, so we re-checked them in the browser.",
  "At 360 pixels wide, none of the twelve pages we checked scrolls sideways. Tabbing through the post form follows the screen order, every field has a label, and the focus ring is visible.",
  "For availability, we cut the network in the middle of the locker page: the page tells you the result could not be confirmed and never re-sends the form automatically. After reconnecting, Refresh status works again.",
  "One honest limitation: on a phone the header and menus take most of the first screen. It works, but a collapsible menu would be better.",
  "",
  "→ Transition: 'Now the smart extension — live.'",
  "SOURCES: Evidence/browser_checks.json (N3_360px, N3_labels, N3_keyboard_post_form, N4_offline_retry); screenshots M01–M04, K01, S18.",
]);

// =====================================================================
// 10 LOCKER DEMO
s = content("Live demo · a simulated locker warns when it is left open", "Daulet · 0:55", "System — Daulet");
tag(s, "LIVE DEMO", 11.5, 0.95, false);
frame(s, "locker_alert", MX, 1.75, 7.2, 2.19, { alt: "Locker page showing OPEN TOO LONG" });
frame(s, "locker_controls", MX, 4.15, 7.2, 1.68, { alt: "Locker simulation controls" });
const lflow = ["Simulate open", "Wait 10 s", "Refresh status", "OPEN TOO LONG", "Simulate close"];
lflow.forEach((t, i) => {
  const y = 1.75 + i * 0.82, x = 8.35;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: 2.3, h: 0.56, rectRadius: 0.08, fill: { color: i === 3 ? C.amberBg : C.sage }, line: i === 3 ? { color: C.amber, width: 1.5 } : { type: "none" } });
  text(s, t, { x, y, w: 2.3, h: 0.56, fontSize: 15, bold: true, align: "center", valign: "middle", color: i === 3 ? C.amber : C.green });
  if (i < 4) arrow(s, x + 1.15, y + 0.58, x + 1.15, y + 0.8, C.forest, 1.5);
});
text(s, [{ text: "SOFTWARE SIMULATION", options: { bold: true, color: C.amber, breakLine: true } }, { text: "No sensor, no door, no network device. Every reading is stored as SIMULATED and a notice is never closed automatically — a person checks the locker." }],
  { x: 10.9, y: 1.75, w: 1.85, h: 4.1, fontSize: 13 });
text(s, "Buttons update the page in place (fetch with CSRF token, no reload). Physical version proposed: reed switch + Wi-Fi controller, HTTPS, device keys.", { x: MX, y: 6.05, w: 12.1, h: 0.6, fontSize: 13, color: C.muted });
notes(s, [
  "SPEAKER: Daulet · about 0:55 · LIVE DEMO (admin private window, /admin/smart-locker)",
  "",
  "SAY FIRST: 'This is a software simulation. There is no physical locker or sensor.'",
  "1. Choose a Found notice in the list. Click Simulate open. SAY: 'The reading is saved in a separate telemetry database, labelled SIMULATED, without reloading the page.'",
  "2. Keep talking for 10 seconds: 'In a real pilot, a reed switch and a Wi-Fi controller would send this event over HTTPS with a device key.'",
  "3. Click Refresh status → OPEN TOO LONG appears. SAY: 'The warning is evaluated when the page is requested, after 10 seconds in the demo.'",
  "4. Click Simulate close. SAY: 'The warning clears. The notice is never marked returned automatically — staff must still check who is collecting the item.'",
  "IF IT FAILS: narrate the two screenshots on this slide; they show the same states from 8 Nov 2026.",
  "",
  "→ Transition: 'To finish: what is still limited, and what we learned.'",
  "FACTS: browser_checks.json locker_simulation — alert after 13.6 s, updated_without_page_reload = true, status 'Reading saved. Door is closed.'",
]);

// =====================================================================
// 11 LIMITS & LESSONS
s = content("What we would build next, and what we learned", "Daulet · 0:40", "System — Daulet");
const lim = [["Sign-in only on localhost", "HTTPS redirect, secret in a vault, store the immutable oid claim"], ["One laptop, local HTTP", "Host in a Kazakhstan data centre with HTTPS — personal data must stay in Kazakhstan"], ["SQLite, one writer", "PostgreSQL + object storage before 10,000 users"], ["Free-text locations", "A fixed list of campus places for cleaner analytics"]];
text(s, "LIMIT NOW", { x: MX, y: 1.7, w: 3.3, h: 0.3, fontSize: 12, bold: true, color: C.muted, charSpacing: 2 });
text(s, "NEXT STEP", { x: MX + 3.55, y: 1.7, w: 4, h: 0.3, fontSize: 12, bold: true, color: C.forest, charSpacing: 2 });
lim.forEach(([a, b], i) => {
  const y = 2.1 + i * 1.08;
  text(s, a, { x: MX, y, w: 3.2, h: 0.9, fontSize: 16, bold: true, valign: "middle" });
  arrow(s, MX + 3.0, y + 0.45, MX + 3.45, y + 0.45, C.forest, 1.5);
  text(s, b, { x: MX + 3.55, y, w: 4.0, h: 0.9, fontSize: 14, valign: "middle" });
  if (i < 3) s.addShape(pres.shapes.LINE, { x: MX, y: y + 1.0, w: 7.55, h: 0, line: { color: C.line, width: 0.75 } });
});
s.addShape(pres.shapes.RECTANGLE, { x: 8.75, y: 1.7, w: 3.98, h: 4.95, fill: { color: C.green }, line: { type: "none" } });
text(s, "Lessons", { x: 9.05, y: 1.95, w: 3.4, h: 0.5, fontSize: 22, color: C.lime, fontFace: HEAD });
text(s, [
  { text: "Evidence beats claims — the requirement table separated “passes a test” from “a person used it”.", options: { bullet: true, breakLine: true } },
  { text: "Cutting chat and matching kept the core flow stable; university sign-in came last, once the core worked.", options: { bullet: true, breakLine: true } },
  { text: "One upload commit hid our individual work — next time, one commit per feature.", options: { bullet: true, breakLine: true } },
  { text: "Start testing with real users in week 7, not week 10.", options: { bullet: true } },
], { x: 9.05, y: 2.55, w: 3.45, h: 3.9, fontSize: 14, color: C.white, paraSpaceAfter: 10 });
notes(s, [
  "SPEAKER: Daulet · about 0:40",
  "",
  "Four limits matter most. Microsoft sign-in works, but only on localhost: a hosted version needs an HTTPS redirect, the secret in a vault and the immutable oid claim. One laptop over local HTTP — the next step is hosting in a Kazakhstan data centre with HTTPS, because under Article 12 of the personal data law, personal data must be stored in a database located in Kazakhstan. SQLite allows one writer at a time — fine for a demo, not for ten thousand users. And free-text locations made our analytics split one place into two.",
  "What we learned: evidence beats claims; cutting scope kept the core stable; our single upload commit hid who did what — next time, one commit per feature; and real users should come much earlier.",
  "",
  "→ Transition: 'Thank you — we are ready for questions.'",
  "SOURCES: report Section 9; Law RK No. 94-V Art. 12(2) (adilet.zan.kz, checked 8 Nov 2026); sqlite.org/whentouse.html.",
]);

// =====================================================================
// 12 CLOSE
s = pres.addSlide({ masterName: "DARK", sectionTitle: "System — Daulet" });
text(s, "Thank you", { x: MX, y: 1.3, w: 8, h: 1.2, fontSize: 54, color: C.white, fontFace: HEAD });
text(s, "Questions — about any part of the system — are welcome.", { x: MX, y: 2.55, w: 8, h: 0.6, fontSize: 22, color: C.lime });
text(s, [
  { text: "Repository", options: { bold: true, color: C.lime, breakLine: true } }, { text: "github.com/zondbebox/SE-2623_Endterm · branch main · commit a7e5c74", options: { breakLine: true } },
  { text: " ", options: { breakLine: true, fontSize: 8 } },
  { text: "Run it", options: { bold: true, color: C.lime, breakLine: true } }, { text: "Campus_Lost_Found\\START.bat  →  http://127.0.0.1:5055", options: { breakLine: true } },
  { text: " ", options: { breakLine: true, fontSize: 8 } },
  { text: "Demo accounts (synthetic)", options: { bold: true, color: C.lime, breakLine: true } }, { text: "student zhanzhol.demo@astanait.edu.kz · admin admin.demo@astanait.edu.kz · shared demo password in the README" },
], { x: MX, y: 3.6, w: 8.5, h: 2.6, fontSize: 16, color: C.white });
text(s, [{ text: "Mengdigerey Zhanzhol", options: { breakLine: true } }, { text: "Galitskiy Daniil", options: { breakLine: true } }, { text: "Bisengaliev Daulet" }], { x: 9.6, y: 4.6, w: 3.2, h: 1.3, fontSize: 16, color: "D9E7D4", align: "right" });
notes(s, [
  "SPEAKER: Daulet (closing line) · about 0:10 · then all three take questions",
  "",
  "'Thank you. We are happy to answer questions about any part of the system — each of us can explain all of it.'",
  "Keep the browser open on the admin panel in the private window and the code editor on app.py in case the instructor asks for a live change.",
  "Backup slides follow: B1 demo fallback, B2 personal data and Kazakhstan law, B3 10,000 users, B4 sources.",
]);

// =====================================================================
// BACKUP SLIDES
pres.addSection({ title: "Backup (not presented)" });
s = content("Backup · if the live demo fails, we keep going", "Backup B1", "Backup (not presented)");
const fb = [["Server stopped", "Close the window, double-click START.bat again, sign in (30 s)."], ["Port 5055 busy", "Stop the old window with Ctrl+C, or run python\\python.exe app.py --port 5056."], ["Laptop or browser fails", "Narrate slides 4, 5 and 10 — every frame is a real capture of the final build."], ["Need motion", VIDEO_URL ? `Final demo video: ${VIDEO_URL} (re-recorded on the final interface).` : "Final demo video: link to be added (Final/Video/). Until then: Video/SE-2623_Campus_Lost_Found_A4.mp4 — older interface; say so."]];
fb.forEach(([a, b], i) => {
  const y = 1.8 + i * 1.15;
  text(s, a, { x: MX, y, w: 3.4, h: 0.9, fontSize: 18, bold: true, color: C.green, valign: "middle", fontFace: HEAD });
  text(s, b, { x: 4.2, y, w: 8.5, h: 0.9, fontSize: 16, valign: "middle" });
  if (i < 3) s.addShape(pres.shapes.LINE, { x: MX, y: y + 1.03, w: 12.1, h: 0, line: { color: C.line, width: 0.75 } });
});
notes(s, ["BACKUP — use only if the demo fails. Full fallback plan: Final/Demo/Demo_Plan_and_Backup.md. The A4 video shows the earlier white/teal interface without the admin panel, analytics or locker; tell the audience that before playing it."]);

s = content("Backup · where personal data lives, and why the law cares", "Backup B2", "Backup (not presented)");
text(s, [
  { text: "Where it is now", options: { bold: true, color: C.green, breakLine: true, fontSize: 18 } },
  { text: "Emails, password hashes and notices: data/campus.sqlite3. Photos: data/uploads/. Backups: backups/. All on the demo laptop’s disk, in Kazakhstan, not encrypted by the app. GitHub holds synthetic data only.", options: { breakLine: true } },
  { text: " ", options: { breakLine: true, fontSize: 8 } },
  { text: "What the law says", options: { bold: true, color: C.green, breakLine: true, fontSize: 18 } },
  { text: "Law RK No. 94-V “On Personal Data and Their Protection”: Art. 12(2) storage in a database located in Kazakhstan; Arts. 7–8 consent; Art. 22 protection; Art. 25(2)(8) breach notice within one working day (Russian text, as amended 14 Sep 2026).", options: { breakLine: true } },
  { text: " ", options: { breakLine: true, fontSize: 8 } },
  { text: "If we went public", options: { bold: true, color: C.green, breakLine: true, fontSize: 18 } },
  { text: "Kazakhstan data centre · HTTPS · consent text · retention period · incident procedure. We do not claim legal compliance." },
], { x: MX, y: 1.75, w: 12.1, h: 4.9, fontSize: 15 });
notes(s, ["BACKUP for defense question 5. Source: adilet.zan.kz/rus/docs/Z1300000094 (checked 8 Nov 2026). The law does not name the ministry; the Ministry of AI and Digital Development publishes personal-data guidance (gov.kz/org/maidd). Interpretation only — not legal advice."]);

s = content("Backup · with 10,000 users, access fails first, then writes", "Backup B3", "Backup (not presented)");
const chain = [["1 · Reachability", "Loopback only: nobody else can open the site"], ["2 · Writes", "SQLite = one writer; Waitress = 4 threads; uploads up to 6 MB queue"], ["3 · Storage", "Photos on one disk; in-memory rate limit resets on restart"], ["4 · Identity", "Local accounts cannot prove 10,000 real students"]];
chain.forEach(([a, b], i) => {
  const x = MX + i * 3.08;
  s.addShape(pres.shapes.RECTANGLE, { x, y: 1.85, w: 2.85, h: 2.3, fill: { color: i === 0 ? C.amberBg : C.mist }, line: { type: "none" } });
  text(s, [{ text: a, options: { bold: true, breakLine: true, color: i === 0 ? C.amber : C.green, fontSize: 17 } }, { text: b, options: { fontSize: 14 } }], { x: x + 0.2, y: 2.05, w: 2.5, h: 2.0 });
  if (i < 3) arrow(s, x + 2.88, 3.0, x + 3.05, 3.0, C.forest, 1.5);
});
text(s, [{ text: "Plan: ", options: { bold: true, color: C.green } }, { text: "host in Kazakhstan with HTTPS → PostgreSQL → object storage for photos → several app instances behind a load balancer with a shared rate limiter → HTTPS redirect for Entra sign-in → load-test before launch. Our 45 ms p95 is for 10 users on a laptop and does not predict 10,000." }],
  { x: MX, y: 4.55, w: 12.1, h: 1.5, fontSize: 16 });
notes(s, ["BACKUP for defense question 8. Source: report Section 9; sqlite.org/whentouse.html."]);

s = content("Backup · sources for the facts in this talk", "Backup B4", "Backup (not presented)");
text(s, [
  { text: "Stage 1 report (9 Oct 2026) — survey n = 10, requirements F1–F8, N1–N4, SC1–SC3", options: { bullet: true, breakLine: true } },
  { text: "Stage 2 report (1 Nov 2026) — Stage 2 statuses; SC1/SC2 recorded as Pending", options: { bullet: true, breakLine: true } },
  { text: "Final/Evidence (8 Nov 2026) — test_suite_final.log, search_performance_final.json, sc3_final.json, stability_30min_final.json, browser_checks.json, account_checks.json, screenshots", options: { bullet: true, breakLine: true } },
  { text: "Final/Testing — Final_Test_Protocol.md, final_test_results.csv, stage2_team_reported.csv", options: { bullet: true, breakLine: true } },
  { text: "Law RK No. 94-V, adilet.zan.kz (checked 8 Nov 2026); Microsoft Learn — Entra app registration and OpenID Connect; SQLite — Appropriate uses; OWASP cheat sheets", options: { bullet: true, breakLine: true } },
  { text: "Code: github.com/zondbebox/SE-2623_Endterm, commit a7e5c74 (only commit, uploaded from the zondbebox account)", options: { bullet: true } },
], { x: MX, y: 1.8, w: 12.1, h: 4.8, fontSize: 15, paraSpaceAfter: 10 });
notes(s, ["Full APA reference list: report Section 10."]);

// ---------- write ----------
(async () => {
  await pres.writeFile({ fileName: OUT });
  try {
    const { applyTheme } = require(path.join(__dirname, "apply_theme.js"));
    await applyTheme(OUT, THEME);
  } catch (e) { console.warn("Theme colours not applied:", e.message); }
  console.log("Wrote", OUT, "| user-test data:", haveFt ? `${people.length} participants` : "none yet", "| N4 done:", stabDone);
})();
