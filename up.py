import os
import subprocess
import random
from pathlib import Path
import requests
import logging
from flask import Flask, request, jsonify, render_template_string

# 配置日志
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[
    logging.FileHandler("app.log"),
    logging.StreamHandler()
])

app = Flask(__name__)

# 配置文件路径
config_file = "config.txt"

# 全局变量
video_folder = ""
output_folder = ""
log_file = ""

# 模板
html_template = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>视频处理应用</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f4f4f4;
        }
        .container {
            max-width: 900px;
            margin: 10px auto;
            padding: 10px 20px 30px 20px;
            background-color: #fff;
            box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
            border-radius: 8px;
        }
        h1 {
            text-align: center;
            color: #333;
            margin-bottom: 20px;
        }
        form {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-top: 10px;
            font-weight: bold;
        }
        input[type="text"], input[type="number"], select {
            width: 90%;
            padding: 5px 10px;
            margin-top: 5px;
            border: 1px solid #ccc;
            border-radius: 4px;
        }
        button {
            display: inline-block;
            padding: 5px 10px;
            margin-top: 10px;
            border: none;
            border-radius: 4px;
            background-color: #28a745;
            color: #fff;
            font-size: 16px;
            cursor: pointer;
        }
        button:hover {
            background-color: #218838;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            max-width: 100%;
            overflow-x: auto;
        }
        table, th, td {
            border: 1px solid #ccc;
        }
        th, td {
            padding: 10px;
            text-align: left;
            max-width: 200px; /* 控制宽度以使溢出效果更明显 */
        }
        th {
            background-color: #f4f4f4;
        }
        td {
            display: -webkit-box;
            -webkit-box-orient: vertical;
            -webkit-line-clamp: 4;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .alert {
            padding: 10px;
            margin-top: 20px;
            background-color: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
            border-radius: 4px;
            width: 90%;
        }
        .vip {
            background: #B0E0E6;
            width: 90%;
            display: block;
            margin-top: 20px;
            padding: 5px;
            text-indent: 10px;
            border-radius: 4px;
            border: 1px solid #b0f0e0;
        }
        @media (max-width: 600px) {
            .container {
                padding: 10px;
            }
            button {
                width: 100%;
                margin-top: 10px;
            }
        }
    </style>
    <script>
        function copyText(button, text) {
            const textarea = document.createElement('textarea');
            textarea.value = text;
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand('copy');
            document.body.removeChild(textarea);
            button.textContent = '已复制';
        }
    </script>
    <script>
    function deleteFolder(folderPath) {
        fetch('/delete_folder', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: new URLSearchParams({
                'folder_path': folderPath
            })
        })
        .then(response => response.json())
        .then(data => {
            alert(data.status); // 这里会显示 "文件夹删除成功"
            location.reload();  // 刷新页面以反映删除后的状态
        })
        .catch(error => console.error('Error:', error));
    }
</script>
</head>
<body>
    <div class="container">
        <h1>视频处理应用</h1>
        <form action="/update_paths" method="post">
            <label for="video_folder">视频文件夹:</label>
            <input type="text" id="video_folder" name="video_folder" value="{{ video_folder }}">

            <label for="output_folder">输出文件夹:</label>
            <input type="text" id="output_folder" name="output_folder" value="{{ output_folder }}">

            <label for="log_file">日志文件:</label>
            <input type="text" id="log_file" name="log_file" value="{{ log_file }}">

            <button type="submit">更新路径</button>
        </form>
        <button onclick="location.reload()">刷新页面</button>
        <button onclick="location.href='/process_videos';">生成任务</button>

        <h2>处理过的文件夹</h2>
        <table>
            <thead>
                <tr>
                    <th>文件夹/文件名称</th>
                    <th>缩略图</th>
                    <th>复制缩略图</th>
                    <th>复制mediainfo</th>
                    <th>mediainfo 文件</th>
                    
                    <th>操作</th>
                </tr>
            </thead>
            <tbody>
                {% for folder in folders %}
                <tr>
                    <td>{{ folder.folder_name }}{% if folder.is_video_file %} (视频文件){% endif %}</td>
                    <td>
                        {% for thumbnail in folder.thumbnails %}
                        [img]{{ thumbnail }}[/img]<br>
                        {% endfor %}
                    </td>
                    <td>
                        <button onclick="copyText(this, `{% for thumbnail in folder.thumbnails %}[img]{{ thumbnail }}[/img]\n{% endfor %}`)">
                            复制缩略图
                        </button>
                    </td>
                    <td>
                        <button onclick="copyText(this, `{{ folder.mediainfo_content }}`)">
                            复制 mediainfo
                        </button>
                    </td>
                    <td>
                        {% for mediainfo in folder.mediainfo_files %}
                        <a href="{{ folder.folder_path }}/{{ mediainfo }}" target="_blank">
                            {{ mediainfo }}
                        </a><br>
                        {% endfor %}
                    </td>
                    
                    <td>
                        <form action="/delete_folder" method="post">
                            <input type="hidden" name="folder_path" value="{{ folder.folder_path }}">
                            <button type="submit">删除</button>
                        </form>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</body>
</html>
"""

def load_config():
    global video_folder, output_folder, log_file
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            lines = f.readlines()
            if len(lines) >= 3:
                video_folder = lines[0].strip()
                output_folder = lines[1].strip()
                log_file = lines[2].strip()
    logging.debug(f"Loaded configuration: video_folder={video_folder}, output_folder={output_folder}, log_file={log_file}")

def set_defaults():
    global video_folder, output_folder, log_file
    if not video_folder:
        video_folder = "/home/downloads"
    if not output_folder:
        output_folder = "/home/pt"
    if not log_file:
        log_file = "/home/pt/pic.log"
    save_config()
    logging.debug(f"Set default configuration: video_folder={video_folder}, output_folder={output_folder}, log_file={log_file}")

def save_config():
    with open(config_file, 'w') as f:
        f.write(f"{video_folder}\n")
        f.write(f"{output_folder}\n")
        f.write(f"{log_file}\n")
    logging.debug("Saved configuration")

def ensure_directories_and_files():
    if not os.path.exists(video_folder):
        os.makedirs(video_folder)
        logging.debug(f"Created video folder: {video_folder}")
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        logging.debug(f"Created output folder: {output_folder}")
    if not os.path.exists(log_file):
        open(log_file, 'a').close()
        logging.debug(f"Created log file: {log_file}")

# 加载配置并确保目录和文件存在
load_config()
set_defaults()
ensure_directories_and_files()

def log_entry(entry):
    with open(log_file, 'a') as log:
        log.write(entry + '\n')
    logging.debug(f"Logged entry: {entry}")

def is_logged(entry, folder_output_path):
    if not os.path.exists(log_file):
        return False

    with open(log_file, 'r') as log:
        log_content = log.read()

    if entry in log_content:
        thumbnails_file = os.path.join(folder_output_path, 'thumbnails.txt')
        mediainfo_files = [f for f in os.listdir(folder_output_path) if f.endswith('_mediainfo.txt')]

        if os.path.exists(thumbnails_file) and os.path.getsize(thumbnails_file) > 0 and mediainfo_files:
            for mediainfo in mediainfo_files:
                mediainfo_path = os.path.join(folder_output_path, mediainfo)
                if os.path.getsize(mediainfo_path) == 0:
                    return False
            return True
        else:
            return False
    return False

def get_processed_folders():
    processed_folders = set()
    folders_list = []

    if os.path.exists(log_file):
        with open(log_file, 'r') as log:
            for line in log:
                if "处理文件夹" in line or "处理文件" in line:
                    folder_name = line.split(": ")[1].strip()
                    folder_output_path = os.path.join(output_folder, folder_name)
                    if os.path.exists(folder_output_path):
                        thumbnails_file = os.path.join(folder_output_path, 'thumbnails.txt')
                        mediainfo_files = [f for f in os.listdir(folder_output_path) if f.endswith('_mediainfo.txt')]

                        thumbnails = []
                        if os.path.exists(thumbnails_file):
                            with open(thumbnails_file, 'r') as th_file:
                                thumbnails = th_file.read().splitlines()

                        mediainfo_content = ""
                        if mediainfo_files:
                            mediainfo_path = os.path.join(folder_output_path, mediainfo_files[0])
                            with open(mediainfo_path, 'r') as mi_file:
                                mediainfo_content = mi_file.read()

                        folder_data = {
                            'folder_name': folder_name,
                            'thumbnails': thumbnails,
                            'mediainfo_files': mediainfo_files,
                            'mediainfo_content': mediainfo_content,
                            'folder_path': folder_output_path,
                            'is_video_file': "处理文件" in line
                        }

                        if folder_name not in processed_folders:
                            processed_folders.add(folder_name)
                            folders_list.append(folder_data)

    logging.debug(f"Processed folders: {folders_list}")
    return folders_list

def clean_deleted_folders():
    if not video_folder:
        return

    existing_folders = {folder_name for folder_name in os.listdir(video_folder) if os.path.isdir(os.path.join(video_folder, folder_name))}

    for folder_name in os.listdir(output_folder):
        folder_output_path = os.path.join(output_folder, folder_name)
        if os.path.isdir(folder_output_path) and folder_name not in existing_folders:
            delete_generated_files(folder_output_path)
            logging.debug(f"Deleted non-existing folder: {folder_name}")

    if os.path.exists(log_file):
        with open(log_file, 'r') as log:
            log_lines = log.readlines()

        with open(log_file, 'w') as log:
            for line in log_lines:
                folder_name = line.split(": ")[-1].strip()
                if folder_name in existing_folders:
                    log.write(line)
                else:
                    logging.debug(f"Deleted log entry for non-existing folder: {folder_name}")

def delete_generated_files(folder_output_path):
    if os.path.exists(folder_output_path):
        for file in os.listdir(folder_output_path):
            os.remove(os.path.join(folder_output_path, file))
        os.rmdir(folder_output_path)
        logging.debug(f"Deleted folder and contents: {folder_output_path}")

def save_mediainfo(video_path, output_path):
    try:
        mediainfo_command = ['mediainfo', video_path]
        mediainfo = subprocess.check_output(mediainfo_command, text=True)
        with open(output_path, 'w') as f:
            f.write(mediainfo)
        logging.debug(f"Saved mediainfo to {output_path}")
    except FileNotFoundError:
        logging.error(f"Error getting mediainfo for {video_path}: mediainfo command not found")
    except Exception as e:
        logging.error(f"Error getting mediainfo for {video_path}: {e}")

def process_video(video_path, video_name, folder_output_path):
    try:
        duration_command = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', video_path]
        duration = float(subprocess.check_output(duration_command).strip())
        screenshot_times = sorted(random.sample(range(0, int(duration)), 4))

        for i, time in enumerate(screenshot_times):
            output_image = os.path.join(folder_output_path, f"{video_name}_screenshot_{i+1}.png")

            if not os.path.exists(output_image) or os.path.getsize(output_image) == 0:
                try:
                    ffmpeg_command = [
                        'ffmpeg', '-y', '-ss', str(time), '-i', video_path,
                        '-vframes', '1', '-q:v', '2', output_image
                    ]

                    subprocess.run(ffmpeg_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

                    if os.path.exists(output_image) and os.path.getsize(output_image) > 10 * 1024 * 1024:
                        try:
                            pngquant_command = ['pngquant', '--force', '--ext', '.png', '--quality', '65-80', output_image]
                            subprocess.run(pngquant_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                        except FileNotFoundError:
                            logging.error(f"Error processing video {video_path}: pngquant not found")
                            logging.error("Please install pngquant using: sudo apt-get install pngquant")

                    with open(output_image, 'rb') as img_file:
                        files = {'img': img_file}
                        data = {
                            'content_type': '0',
                            'max_th_size': '420'
                        }
                        response = requests.post('https://api.pixhost.to/images', files=files, data=data)
                        response_data = response.json()
                        show_url = response_data['show_url']
                        new_url = show_url.replace('https://pixhost.to/show/', 'https://img97.pixhost.to/images/')
                        with open(os.path.join(folder_output_path, 'thumbnails.txt'), 'a') as th_file:
                            th_file.write(f"{new_url}\n")
                        logging.debug(f"Uploaded {output_image} to {new_url}")

                except subprocess.CalledProcessError as e:
                    logging.error(f"Error processing video {video_path}: {e}")
                    break

        mediainfo_path = os.path.join(folder_output_path, f"{video_name}_mediainfo.txt")
        if not os.path.exists(mediainfo_path) or os.path.getsize(mediainfo_path) == 0:
            save_mediainfo(video_path, mediainfo_path)

    except Exception as e:
        logging.error(f"Error processing video {video_path}: {e}")

def process_folder(root, files):
    folder_name = os.path.basename(root)
    folder_output_path = os.path.join(output_folder, folder_name)
    os.makedirs(folder_output_path, exist_ok=True)

    log_entry_text = f"处理文件夹: {folder_name}"
    if is_logged(log_entry_text, folder_output_path):
        logging.debug(f"{folder_name} 已经处理过，跳过...")
        return

    video_files = [os.path.join(root, f) for f in files if f.lower().endswith(('.mkv','.iso','.ts','.mp4','.avi','.rmvb','.wmv','.m2ts','.mpg','.flv','.rm','.mov'))]

    if not video_files:
        logging.debug(f"文件夹 {folder_name} 中没有找到视频文件，仍然创建文件夹。")
        log_entry(log_entry_text)
        return

    video_file = random.choice(video_files)
    video_name = Path(video_file).stem

    process_video(video_file, video_name, folder_output_path)
    log_entry(log_entry_text)

def process_all_videos(video_folder, output_folder):
    # 处理根文件夹中的视频文件
    for root, dirs, files in os.walk(video_folder):
        if Path(root) == Path(video_folder):
            video_files = [os.path.join(root, f) for f in files if f.lower().endswith(('.ts','.mp4', '.avi', '.mkv', '.mov', '.flv'))]
            for video_file in video_files:
                video_name = Path(video_file).stem
                folder_output_path = os.path.join(output_folder, video_name)
                os.makedirs(folder_output_path, exist_ok=True)
                process_video(video_file, video_name, folder_output_path)
                log_entry(f"处理文件: {video_name}")

    # 处理子文件夹中的第一个视频文件
    for root, dirs, files in os.walk(video_folder):
        if Path(root).parent == Path(video_folder):
            process_folder(root, files)

@app.route('/')
def index():
    logging.debug("Rendering index page")
    folders = get_processed_folders()
    return render_template_string(html_template, video_folder=video_folder, output_folder=output_folder, log_file=log_file, folders=folders)

@app.route('/update_paths', methods=['POST'])
def update_paths():
    global video_folder, output_folder, log_file
    video_folder = request.form['video_folder']
    output_folder = request.form['output_folder']
    log_file = request.form['log_file']

    if output_folder and not os.path.exists(output_folder):
        os.makedirs(output_folder, exist_ok=True)
        logging.debug(f"Created output folder: {output_folder}")

    save_config()
    ensure_directories_and_files()
    logging.debug("Configuration updated")

    folders = get_processed_folders()

    return render_template_string(html_template, video_folder=video_folder, output_folder=output_folder, log_file=log_file, folders=folders)

@app.route('/process_videos', methods=['GET'])
def process_videos():
    logging.debug("Processing videos")
    clean_deleted_folders()
    process_all_videos(video_folder, output_folder)
    folders = get_processed_folders()
    return render_template_string(html_template, video_folder=video_folder, output_folder=output_folder, log_file=log_file, folders=folders)

@app.route('/delete_folder', methods=['POST'])
def delete_folder():
    folder_path = request.form['folder_path']
    delete_generated_files(folder_path)
    logging.debug(f"Deleted folder: {folder_path}")
    
    # 直接返回成功消息
    return jsonify(status="文件夹删除成功")

if __name__ == '__main__':
    logging.debug("Starting Flask application")
    app.run(debug=True, host='0.0.0.0', port=45678)
