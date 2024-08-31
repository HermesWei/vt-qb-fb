#!/bin/bash





echo "+---------------------------------------------+"
echo "| 正在安装必要的工具                          |"
echo "+---------------------------------------------+"
apt update -y 

if [ $? -ne 0 ]; then
    echo "安装工具失败，脚本退出"
    exit 1
fi

echo "+---------------------------------------------+"
echo "| 正在安装Docker                              |"
echo "+---------------------------------------------+"
if ! command -v docker &> /dev/null; then
          echo "Docker 未安装,现在开始安装。"
          
apt update
apt install -y docker docker.io  apparmor

fi 


echo "+---------------------------------------------+"
echo "| 更改时区                                    |"
echo "+---------------------------------------------+"
timedatectl set-timezone Asia/Shanghai

echo "+---------------------------------------------+"
echo "| 正在下载配置文件...                         |"
echo "+---------------------------------------------+"
wget -P /root/fj_admin/qb  https://github.com/lifujie25/lifj/raw/main/qb.tar.gz
wget -P /root/fj_admin/fb  https://github.com/lifujie25/lifj/raw/main/fb.tar.gz
wget -P /root/fj_admin/vt  https://github.com/lifujie25/lifj/raw/main/vt.tar.gz

if [ $? -ne 0 ]; then
    echo "下载压缩包失败，脚本退出"
    exit 1
fi

echo "+---------------------------------------------+"
echo "| 正在解压配置文件                           |"
echo "+---------------------------------------------+"
tar -xvf /root/fj_admin/qb/qb.tar.gz -C /root/fj_admin/qb
tar -xvf /root/fj_admin/fb/fb.tar.gz -C /root/fj_admin/fb
tar -xvf /root/fj_admin/vt/vt.tar.gz -C /root/fj_admin/vt

if [ $? -ne 0 ]; then
    echo "解压压缩包失败，脚本退出"
    exit 1
fi


echo "+---------------------------------------------+"
echo "| 正在删除残留文件                            |"
echo "+---------------------------------------------+"
rm -rf /root/fj_admin/qb/qb.tar.gz  /root/fj_admin/fb/fb.tar.gz  /root/fj_admin/vt/vt.tar.gz


if [ $? -ne 0 ]; then
    echo "删除失败，脚本退出"
    exit 1
fi

echo "+---------------------------------------------+"
echo "| 构建Docker容器                              |"
echo "+---------------------------------------------+"
docker run -d --name vertex --restart unless-stopped --network host -v /root/fj_admin/vt:/vertex -e TZ=Asia/Shanghai lswl/vertex:stable
docker run -d --name qbittorrent --net=host -e PUID=1000 -e PGID=1000 -e TZ=Asia/Shanghai -e WEBUI_PORT=8989 -p 8989:8989 -p 45000:45000 -p 45000:45000/udp -v /root/fj_admin/qb/config:/config -v /home/downloads:/downloads -v /root:/root --restart unless-stopped lscr.io/linuxserver/qbittorrent:14.3.9 
docker run -d --name filebrowser --restart=unless-stopped -e PUID=1000 -e PGID=1000 -e WEB_PORT=18082 -e FB_AUTH_SERVER_ADDR=127.0.0.1 -p 18082:18082 -v /root/fj_admin/fb/config:/config -v /home/downloads:/myfiles --mount type=tmpfs,destination=/tmp 80x86/filebrowser

echo "+---------------------------------------------+"
echo "| 重启所有Docker容器                          |"
echo "+---------------------------------------------+"
docker restart $(docker ps -q)

echo "+---------------------------------------------+"
echo "| 脚本执行完毕！                              |"
echo "+---------------------------------------------+"
