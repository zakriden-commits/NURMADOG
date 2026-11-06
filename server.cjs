const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const root = __dirname;
const types = {'.html':'text/html; charset=utf-8','.css':'text/css','.js':'text/javascript','.cjs':'text/javascript','.jpg':'image/jpeg','.jpeg':'image/jpeg','.png':'image/png','.ico':'image/x-icon'};
http.createServer((req,res) => {
  let name;
  try { name = decodeURIComponent(new URL(req.url, 'http://localhost').pathname); } catch { res.writeHead(400).end(); return; }
  if (name === '/') name = '/index.html';
  if (!(name === '/index.html' || name === '/style.css' || name === '/game.js' || name === '/rules.cjs' || name.startsWith('/assets/'))) {res.writeHead(404).end();return;}
  const file = path.resolve(root, '.' + name);
  if (!file.startsWith(root + path.sep)) {res.writeHead(403).end();return;}
  fs.readFile(file,(err,data) => {if(err) {res.writeHead(404).end();return;} res.writeHead(200,{'Content-Type':types[path.extname(file)] || 'application/octet-stream'}).end(data);});
}).listen(Number(process.env.PORT) || 3000,'0.0.0.0',() => console.log('САСНЫЙ: http://0.0.0.0:3000'));
