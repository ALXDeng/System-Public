// Minimal static server for previewing grid/*.html
const http = require("http"), fs = require("fs"), path = require("path");
const root = path.join(__dirname, "..", "grid");
http.createServer((req, res) => {
  const p = path.join(root, decodeURIComponent(req.url.split("?")[0]).replace(/^\/+/, "") || "heat-med-review.html");
  if (!p.startsWith(root)) { res.writeHead(403); return res.end(); }
  fs.readFile(p, (e, b) => {
    if (e) { res.writeHead(404); return res.end("not found"); }
    res.writeHead(200, {"content-type": p.endsWith(".html") ? "text/html; charset=utf-8" : "application/octet-stream"});
    res.end(b);
  });
}).listen(+process.env.PORT || 8765);
