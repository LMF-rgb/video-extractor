"""手机访问服务器 - 在电脑上运行，手机浏览器打开就能下载视频"""
import os, sys, json, threading
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, jsonify, send_from_directory
from video_downloader import VideoExtractor, detect_platform
from video_downloader.utils import format_bytes, format_speed, get_default_download_dir

app = Flask(__name__)
extractor = VideoExtractor()
progress_store = {}

@app.route('/')
def index():
    return '''
<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>视频提取器</title><style>
*{margin:0;padding:0;box-sizing:border-box}body{font-family:system-ui;background:#1a1a2e;color:#eee;padding:15px;max-width:500px;margin:auto}
h1{text-align:center;color:#89b4fa;margin:10px 0}h3{color:#6c7086;font-size:13px;text-align:center;margin-bottom:15px}
input,select,button{width:100%;padding:12px;margin:6px 0;border-radius:8px;border:1px solid #444;background:#313244;color:#eee;font-size:15px}
button{background:#89b4fa;color:#1e1e2e;font-weight:bold;cursor:pointer}button:active{opacity:.8}
.card{background:#181825;border-radius:10px;padding:12px;margin:8px 0}
.progress{background:#333;border-radius:6px;height:10px;overflow:hidden;margin:5px 0}
.bar{background:#a6e3a1;height:100%;width:0;transition:width .3s}
.platform{display:inline-block;padding:2px 8px;border-radius:10px;font-size:11px;margin:2px}
</style></head><body>
<h1>🎬 视频提取器</h1><h3>B站 | 抖音 | YouTube | 小红书 | 快手 | 微博 | 西瓜</h3>
<div class="card"><input id="url" placeholder="粘贴视频链接..." autofocus>
<button onclick="add()">➕ 添加</button></div>
<div id="list"></div>
<div class="card" id="status" style="text-align:center;color:#6c7086">就绪</div>
<script>
let items=[];
function add(){
  let u=document.getElementById('url').value.trim();
  if(!u)return;
  fetch('/add',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:u})})
  .then(r=>r.json()).then(d=>{if(d.ok){items.push(d.item);render();document.getElementById('url').value='';}})}
function dl(i){
  document.getElementById('status').innerHTML='⬇ 下载中...';
  fetch('/download/'+i).then(r=>r.json()).then(d=>{if(d.ok){items[i].status='✅ 完成';items[i].path=d.path;render()}else{items[i].status='❌ 失败';items[i].err=d.error;render()}})}
function render(){
  document.getElementById('list').innerHTML=items.map((it,i)=>`<div class="card"><b>${it.platform||'?'}</b> ${it.url.slice(0,50)}...<br>
  <span id="s${i}">${it.status||'排队中'}</span>
  ${it.status!='✅ 完成'?`<button onclick="dl(${i})" style="width:auto;padding:6px 15px;margin-top:5px">⬇ 下载</button>`:''}
  ${it.path?`<br><small>📁 ${it.path}</small>`:''}
  ${it.err?`<br><small style="color:#f38ba8">${it.err}</small>`:''}
  </div>`).join('')}
setInterval(render,2000);
</script></body></html>'''

@app.route('/add', methods=['POST'])
def add():
    data = request.get_json()
    url = data.get('url', '').strip()
    if not url:
        return jsonify(ok=False, error='空链接')
    p = detect_platform(url)
    return jsonify(ok=True, item={
        'url': url,
        'platform': f'{p.icon} {p.name}' if p else '未知',
        'status': '排队中'
    })

@app.route('/download/<int:idx>')
def download(idx):
    # Simple: just use the last added URL from state
    # In production we'd have proper state management
    url = request.args.get('url', '')
    if not url:
        return jsonify(ok=False, error='缺少url参数')

    def cb(prog):
        progress_store[url] = {'pct': prog.percent, 'speed': format_speed(prog.speed_bytes)}

    result = extractor.download(url=url, progress_callback=cb)
    if result.success:
        return jsonify(ok=True, path=os.path.basename(result.output_path), size=format_bytes(result.file_size))
    else:
        return jsonify(ok=False, error=result.error[:200])

def main():
    import socket
    # Get local IP
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except:
        ip = '127.0.0.1'
    finally:
        s.close()

    print(f'''
==========================================
    Phone Video Extractor
    Open on your phone:
    http://{ip}:8080
    Ctrl+C to stop
==========================================
    ''')
    app.run(host='0.0.0.0', port=8080, debug=False)

if __name__ == '__main__':
    main()
