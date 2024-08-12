import os
import subprocess
import requests
from pathlib import Path
import random
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

# 初始化路径为空
video_folder = ""
output_folder = ""
log_file = ""

# 配置文件名
config_file = "config.txt"

# 尝试加载已有配置
def load_config():
    global video_folder, output_folder, log_file
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            lines = f.readlines()
            if len(lines) >= 3:
                video_folder = lines[0].strip()
                output_folder = lines[1].strip()
                log_file = lines[2].strip()

# 检查并设置默认值
def set_defaults():
    global video_folder, output_folder, log_file
    if not video_folder:
        video_folder = "/home/downloads"
    if not output_folder:
        output_folder = "/home/pt"
    if not log_file:
        log_file = "/home/pt/pic.log"
    save_config()


# 保存配置到文件
def save_config():
    with open(config_file, 'w') as f:
        f.write(f"{video_folder}\n")
        f.write(f"{output_folder}\n")
        f.write(f"{log_file}\n")

# 调用时加载配置
load_config()
set_defaults()

def log_entry(entry):
    with open(log_file, 'a') as log:
        log.write(entry + '\n')

def is_logged(entry, folder_output_path):
    if not os.path.exists(log_file):
        return False

    with open(log_file, 'r') as log:
        log_content = log.read()

    if entry in log_content:
        # 检查缩略图和 mediainfo 文件是否存在且不为空
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

def save_mediainfo(video_path, output_path):
    try:
        mediainfo_command = ['mediainfo', video_path]
        mediainfo = subprocess.check_output(mediainfo_command, text=True)
        with open(output_path, 'w') as f:
            f.write(mediainfo)
        print(f"已保存 mediainfo 到 {output_path}")
    except FileNotFoundError:
        print(f"获取 mediainfo 时出错 {video_path}: mediainfo 命令未找到，请确保已安装 mediainfo。")
    except Exception as e:
        print(f"获取 mediainfo 时出错 {video_path}: {e}")

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
                            print(f"处理视频 {video_path} 时出错: pngquant 未找到，请确保已安装 pngquant。")
                            print("请执行以下命令进行安装：")
                            print("sudo apt-get install pngquant")

                    # 上传并记录缩略图地址
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
                        print(f"已上传 {output_image} 到 {new_url}")

                except subprocess.CalledProcessError as e:
                    print(f"处理视频 {video_path} 时出错: {e}")
                    break

        mediainfo_path = os.path.join(folder_output_path, f"{video_name}_mediainfo.txt")
        if not os.path.exists(mediainfo_path) or os.path.getsize(mediainfo_path) == 0:
            save_mediainfo(video_path, mediainfo_path)

    except Exception as e:
        print(f"处理视频 {video_path} 时出错: {e}")

def get_processed_folders():
    processed_folders = set()
    folders_list = []

    if os.path.exists(log_file):
        with open(log_file, 'r') as log:
            for line in log:
                if "处理文件夹" in line:
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
                            'folder_path': folder_output_path
                        }

                        if folder_name not in processed_folders:
                            processed_folders.add(folder_name)
                            folders_list.append(folder_data)

    return folders_list

def delete_generated_files(folder_output_path):
    if os.path.exists(folder_output_path):
        for file in os.listdir(folder_output_path):
            os.remove(os.path.join(folder_output_path, file))
        os.rmdir(folder_output_path)

# 定义 HTML 模板作为字符串
html_template = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>视频处理应用</title>
    <script>
        function copyText(text) {
            const textarea = document.createElement('textarea');
            textarea.value = text;
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand('copy');
            document.body.removeChild(textarea);
            alert('已复制到剪贴板');
        }
    </script>
</head>
<body>
    <h1>视频处理应用</h1>
    <form action="/update_paths" method="post">
        <label for="video_folder">视频文件夹:</label>
        <input type="text" id="video_folder" name="video_folder" value="{{ video_folder }}"><br><br>
        <label for="output_folder">输出文件夹:</label>
        <input type="text" id="output_folder" name="output_folder" value="{{ output_folder }}"><br><br>
        <label for="log_file">日志文件:</label>
        <input type="text" id="log_file" name="log_file" value="{{ log_file }}"><br><br>
        <input type="submit" value="更新路径">
    </form>
    <button onclick="location.reload()">刷新页面</button>
    <button onclick="location.href='/process_videos';">生成任务</button>

    <h2>处理过的文件夹</h2>
    <table border="1">
                <tr>
            <th>文件夹名称</th>
            <th>缩略图</th>
            <th>复制缩略图链接</th>
            <th>mediainfo 文件</th>
            <th>复制 mediainfo 内容</th>
            <th>操作</th>
        </tr>
                {% for folder in folders %}
        <tr>
            <td>{{ folder.folder_name }}</td>
            <td>
                {% for thumbnail in folder.thumbnails %}
                [img]{{ thumbnail }}[/img]<br>
                {% endfor %}
            </td>
            <td>
                <button onclick="copyText(`{% for thumbnail in folder.thumbnails %}[img]{{ thumbnail }}[/img]\n{% endfor %}`)">
                    一键复制所有缩略图链接
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
                <button onclick="copyText(`{{ folder.mediainfo_content }}`)">
                    复制 mediainfo 内容
                </button>
            </td>
            <td>
                <form action="/delete_folder" method="post">
                    <input type="hidden" name="folder_path" value="{{ folder.folder_path }}">
                    <input type="submit" value="删除">
                </form>
            </td>
        </tr>
        {% endfor %}
    </table>
</body>
</html>
"""

@app.route('/')
def index():
    folders = get_processed_folders()
    return render_template_string(html_template, video_folder=video_folder, output_folder=output_folder, log_file=log_file, folders=folders)

@app.route('/update_paths', methods=['POST'])
def update_paths():
    global video_folder, output_folder, log_file
    video_folder = request.form['video_folder']
    output_folder = request.form['output_folder']
    log_file = request.form['log_file']

    # 如果output_folder不存在，创建它
    if output_folder and not os.path.exists(output_folder):
        os.makedirs(output_folder, exist_ok=True)
        print(f"已创建输出文件夹: {output_folder}")

    save_config()

    folders = get_processed_folders()

    return render_template_string(html_template, video_folder=video_folder, output_folder=output_folder, log_file=log_file, folders=folders)

def process_folder(root, files):
    folder_name = os.path.basename(root)
    folder_output_path = os.path.join(output_folder, folder_name)
    os.makedirs(folder_output_path, exist_ok=True)

    log_entry_text = f"处理文件夹: {folder_name}"
    if is_logged(log_entry_text, folder_output_path):
        print(f"{folder_name} 已经处理过，跳过...")
        return

    video_files = [os.path.join(root, f) for f in files if f.lower().endswith(('.mp4', '.avi', '.mkv', '.mov', '.flv'))]

    if not video_files:
        print(f"文件夹 {folder_name} 中没有找到视频文件，跳过处理。")
        return

    video_file = random.choice(video_files)
    video_name = Path(video_file).stem

    # 处理视频
    process_video(video_file, video_name, folder_output_path)
    log_entry(log_entry_text)

# 确保在 process_videos 函数中正确调用 process_folder
@app.route('/process_videos', methods=['GET'])
def process_videos():
    # 检查并删除已删除的文件夹及其对应的记录和输出
    clean_deleted_folders()
    
    for root, dirs, files in os.walk(video_folder):
        if Path(root).parent == Path(video_folder):
            process_folder(root, files)

    folders = get_processed_folders()
    return render_template_string(html_template, video_folder=video_folder, output_folder=output_folder, log_file=log_file, folders=folders)

def clean_deleted_folders():
    # 获取video_folder中的所有文件夹名称
    existing_folders = {folder_name for folder_name in os.listdir(video_folder) if os.path.isdir(os.path.join(video_folder, folder_name))}

    # 检查output_folder中的文件夹，并删除那些不在video_folder中的文件夹
    for folder_name in os.listdir(output_folder):
        folder_output_path = os.path.join(output_folder, folder_name)
        if os.path.isdir(folder_output_path) and folder_name not in existing_folders:
            # 删除output_folder中的文件夹
            delete_generated_files(folder_output_path)
            print(f"删除了不再存在的文件夹: {folder_name}")

    # 清理日志文件中的记录
    if os.path.exists(log_file):
        with open(log_file, 'r') as log:
            log_lines = log.readlines()

        with open(log_file, 'w') as log:
            for line in log_lines:
                folder_name = line.split(": ")[-1].strip()
                if folder_name in existing_folders:
                    log.write(line)
                else:
                    print(f"删除了日志中的记录: {folder_name}")

# 定义 delete_generated_files 函数
def delete_generated_files(folder_output_path):
    if os.path.exists(folder_output_path):
        for file in os.listdir(folder_output_path):
            os.remove(os.path.join(folder_output_path, file))
        os.rmdir(folder_output_path)
        print(f"已删除 {folder_output_path} 文件夹及其内容")

    
@app.route('/delete_folder', methods=['POST'])
def delete_folder():
    folder_path = request.form['folder_path']
    delete_generated_files(folder_path)
    return jsonify(status="文件夹删除成功")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=45678)