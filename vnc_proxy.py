#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版VNC代理服务器
采用新的设计思路，确保连接管理的可靠性
"""

import socket
import threading
import time
import tkinter as tk
from tkinter import messagebox
import logging
from datetime import datetime
import queue

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('vnc_proxy_simple.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SimpleVNCProxy:
    def __init__(self, vnc_host="127.0.0.1", vnc_port=5900, proxy_port=5901):
        self.vnc_host = vnc_host
        self.vnc_port = vnc_port
        self.proxy_port = proxy_port
        
        # 连接状态
        self.active_session = None  # 当前活跃的会话
        self.server_socket = None
        self.is_running = False
        
        # 等待队列
        self.waiting_queue = queue.Queue()
        
        # GUI
        self.root = None
        self.decision_dialog = None
        self.user_decision = None
        
        # 被拒绝的客户端冷却
        self.rejected_ips = {}  # ip -> reject_time
        self.grace_period = 60  # 1分钟冷却期
        
    def start_server(self):
        """启动代理服务器"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('0.0.0.0', self.proxy_port))
            self.server_socket.listen(5)
            self.is_running = True
            
            logger.info(f"简化VNC代理服务器启动在端口 {self.proxy_port}")
            
            while self.is_running:
                try:
                    client_socket, client_addr = self.server_socket.accept()
                    logger.info(f"新客户端连接: {client_addr}")
                    
                    # 在新线程中处理
                    threading.Thread(
                        target=self.handle_new_client,
                        args=(client_socket, client_addr),
                        daemon=True
                    ).start()
                    
                except socket.error as e:
                    if self.is_running:
                        logger.error(f"接受连接错误: {e}")
                        
        except Exception as e:
            logger.error(f"启动服务器失败: {e}")
            
    def handle_new_client(self, client_socket, client_addr):
        """处理新客户端连接"""
        client_ip = client_addr[0]
        
        try:
            # 检查冷却期
            if self.is_in_grace_period(client_ip):
                logger.info(f"客户端 {client_addr} 在冷却期内，拒绝连接")
                self.send_refuse_and_close(client_socket, "服务器正被其他用户使用，请稍后再试。")
                return
                
            # 如果没有活跃会话，直接连接
            if self.active_session is None:
                self.create_new_session(client_socket, client_addr)
                return
                
            # 有活跃会话，需要用户决策
            logger.info(f"有活跃会话，新客户端 {client_addr} 等待决策")
            decision = self.get_user_decision(client_addr)
            
            if decision == "allow_new":
                # 断开旧会话
                self.disconnect_current_session()
                # 创建新会话
                self.create_new_session(client_socket, client_addr)
            else:
                # 拒绝新连接，并将新用户IP加入冷却列表
                self.rejected_ips[client_ip] = time.time()
                logger.info(f"新用户 {client_addr} 被拒绝，加入1分钟冷却列表")
                self.send_refuse_and_close(client_socket, "服务器正被其他用户使用，请稍后再试。")
                
        except Exception as e:
            logger.error(f"处理客户端 {client_addr} 时出错: {e}")
            try:
                client_socket.close()
            except:
                pass
                
    def create_new_session(self, client_socket, client_addr):
        """创建新的VNC会话"""
        try:
            # 连接到VNC服务器
            vnc_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            vnc_socket.connect((self.vnc_host, self.vnc_port))
            
            # 创建会话对象
            session = {
                'client_socket': client_socket,
                'vnc_socket': vnc_socket,
                'client_addr': client_addr,
                'start_time': datetime.now(),
                'active': True
            }
            
            self.active_session = session
            logger.info(f"为客户端 {client_addr} 创建新VNC会话")
            
            # 启动数据转发
            self.start_forwarding(session)
            
        except Exception as e:
            logger.error(f"创建VNC会话失败: {e}")
            self.send_refuse_and_close(client_socket, "无法连接到VNC服务器，请稍后再试。")
            
    def start_forwarding(self, session):
        """启动数据转发"""
        def forward_data(src, dst, direction):
            try:
                while session['active']:
                    data = src.recv(4096)
                    if not data:
                        logger.info(f"数据转发结束: {direction}")
                        break
                    dst.send(data)
            except Exception as e:
                logger.info(f"数据转发异常: {direction} - {e}")
            finally:
                # 只有当前会话结束时才清理
                if session == self.active_session:
                    self.cleanup_session()
                    
        # 启动双向转发
        threading.Thread(
            target=forward_data,
            args=(session['client_socket'], session['vnc_socket'], "客户端->VNC"),
            daemon=True
        ).start()
        
        threading.Thread(
            target=forward_data,
            args=(session['vnc_socket'], session['client_socket'], "VNC->客户端"),
            daemon=True
        ).start()
        
    def disconnect_current_session(self):
        """断开当前会话"""
        if self.active_session:
            session = self.active_session
            client_ip = session['client_addr'][0]
            
            # 添加到冷却列表
            self.rejected_ips[client_ip] = time.time()
            
            logger.info(f"断开当前会话: {session['client_addr']}")
            
            # 标记为非活跃
            session['active'] = False
            
            # 关闭连接
            try:
                session['client_socket'].close()
                session['vnc_socket'].close()
            except:
                pass
                
            self.active_session = None
            
    def cleanup_session(self):
        """清理会话"""
        if self.active_session:
            logger.info(f"清理会话: {self.active_session['client_addr']}")
            self.active_session['active'] = False
            try:
                self.active_session['client_socket'].close()
                self.active_session['vnc_socket'].close()
            except:
                pass
            self.active_session = None
            
    def get_user_decision(self, new_client_addr):
        """获取用户决策"""
        if not self.root:
            # 无GUI模式，默认拒绝
            return "keep_current"
            
        # GUI模式，显示决策对话框
        self.user_decision = None
        self.root.after(0, lambda: self.show_decision_dialog(new_client_addr))
        
        # 等待用户决策，最多5秒
        start_time = time.time()
        while self.user_decision is None and (time.time() - start_time) < 5:
            time.sleep(0.1)
            
        if self.user_decision is None:
            # 超时，默认允许新用户
            return "allow_new"
            
        return self.user_decision
        
    def show_decision_dialog(self, new_client_addr):
        """显示决策对话框"""
        if self.decision_dialog:
            return
            
        self.decision_dialog = tk.Toplevel(self.root)
        self.decision_dialog.title("新连接请求")
        self.decision_dialog.geometry("500x300")
        self.decision_dialog.resizable(False, False)
        self.decision_dialog.attributes('-topmost', True)
        self.decision_dialog.focus_force()
        
        # 主容器
        main_container = tk.Frame(self.decision_dialog)
        main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)
        
        # 消息标签
        msg = f"新客户端 {new_client_addr} 请求连接\n\n您要断开当前连接让新用户使用吗？"
        msg_label = tk.Label(main_container, text=msg, font=('Arial', 14),
                           wraplength=400, justify='center')
        msg_label.pack(pady=(0, 20))
        
        # 倒计时标签
        self.countdown_var = tk.StringVar()
        countdown_label = tk.Label(main_container, textvariable=self.countdown_var,
                                 font=('Arial', 16, 'bold'), fg='red')
        countdown_label.pack(pady=(0, 30))
        
        # 按钮容器
        button_container = tk.Frame(main_container)
        button_container.pack(pady=20)
        
        # 按钮样式
        btn_style = {
            'font': ('Arial', 12, 'bold'),
            'width': 18,
            'height': 3,
            'relief': 'raised',
            'bd': 3
        }
        
        # 继续使用按钮
        continue_btn = tk.Button(
            button_container,
            text="我还要继续使用",
            bg='#2E8B57', fg='white',
            activebackground='#228B22',
            command=lambda: self.make_decision("keep_current"),
            **btn_style
        )
        continue_btn.pack(side=tk.LEFT, padx=20)
        
        # 让新用户连接按钮
        new_user_btn = tk.Button(
            button_container,
            text="让新用户连接",
            bg='#DC143C', fg='white',
            activebackground='#B22222',
            command=lambda: self.make_decision("allow_new"),
            **btn_style
        )
        new_user_btn.pack(side=tk.LEFT, padx=20)
        
        # 启动倒计时
        self.start_decision_countdown()
        
    def start_decision_countdown(self):
        """启动决策倒计时"""
        self.countdown_seconds = 5
        self.update_decision_countdown()
        
    def update_decision_countdown(self):
        """更新决策倒计时"""
        if self.countdown_seconds > 0:
            self.countdown_var.set(f"倒计时: {self.countdown_seconds} 秒")
            self.countdown_seconds -= 1
            if self.root:
                self.root.after(1000, self.update_decision_countdown)
        else:
            self.countdown_var.set("时间到！自动让新用户连接")
            if self.root:
                self.root.after(1000, lambda: self.make_decision("allow_new"))
            
    def make_decision(self, decision):
        """做出决策"""
        self.user_decision = decision
        if self.decision_dialog:
            self.decision_dialog.destroy()
            self.decision_dialog = None
            
    def is_in_grace_period(self, client_ip):
        """检查是否在冷却期"""
        # 如果没有活跃会话，不应该有冷却时间限制
        if self.active_session is None:
            return False
            
        if client_ip not in self.rejected_ips:
            return False
            
        reject_time = self.rejected_ips[client_ip]
        if time.time() - reject_time > self.grace_period:
            del self.rejected_ips[client_ip]
            return False
            
        return True
        
    def send_refuse_and_close(self, client_socket, message):
        """发送拒绝消息并关闭连接"""
        try:
            # 按照RFB协议3.3/3.7/3.8规范发送连接失败消息
            
            # 1. 发送RFB协议版本
            rfb_version = b"RFB 003.008\n"
            client_socket.send(rfb_version)
            
            # 2. 等待客户端发送版本回复
            try:
                client_version = client_socket.recv(12)
                logger.info(f"客户端版本: {client_version}")
            except:
                pass
            
            # 3. 发送安全类型数量 (0 = 连接失败)
            security_types = b"\x00"  # 0个安全类型表示连接失败
            client_socket.send(security_types)
            
            # 4. 发送失败原因长度和内容
            reason = "服务器正被其他用户使用，请稍后再试。"
            reason_bytes = reason.encode('utf-8')  # 使用UTF-8编码中文
            reason_length = len(reason_bytes).to_bytes(4, byteorder='big')
            
            client_socket.send(reason_length)
            client_socket.send(reason_bytes)
            
            logger.info(f"已发送RFB拒绝消息: {reason}")
            
            # 延迟关闭，确保消息发送完成
            time.sleep(0.3)
            
        except Exception as e:
            logger.error(f"发送拒绝消息失败: {e}")
        finally:
            try:
                client_socket.close()
            except:
                pass
                
    def start_gui(self):
        """启动GUI"""
        self.root = tk.Tk()
        self.root.title("简化VNC代理服务器")
        self.root.geometry("400x300")
        
        # 主框架
        frame = tk.Frame(self.root, padx=20, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        tk.Label(frame, text="简化VNC代理服务器", 
                font=('微软雅黑', 16, 'bold')).pack(pady=10)
        
        # 状态
        self.status_var = tk.StringVar(value="服务器未启动")
        tk.Label(frame, textvariable=self.status_var, 
                font=('微软雅黑', 12)).pack(pady=10)
        
        # 连接信息
        self.conn_var = tk.StringVar(value="无客户端连接")
        tk.Label(frame, textvariable=self.conn_var,
                font=('微软雅黑', 10)).pack(pady=5)
        
        # 按钮
        btn_frame = tk.Frame(frame)
        btn_frame.pack(pady=20)
        
        self.start_btn = tk.Button(btn_frame, text="启动服务器",
                                  command=self.start_server_gui)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = tk.Button(btn_frame, text="停止服务器",
                                 command=self.stop_server, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        # 启动状态更新
        self.update_gui_status()
        
        self.root.mainloop()
        
    def start_server_gui(self):
        """从GUI启动服务器"""
        threading.Thread(target=self.start_server, daemon=True).start()
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        
    def stop_server(self):
        """停止服务器"""
        self.is_running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        if self.active_session:
            self.cleanup_session()
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        
    def update_gui_status(self):
        """更新GUI状态"""
        if self.root:
            if self.is_running:
                self.status_var.set(f"服务器运行中 - 端口 {self.proxy_port}")
            else:
                self.status_var.set("服务器未启动")
                
            if self.active_session:
                addr = self.active_session['client_addr']
                start_time = self.active_session['start_time'].strftime('%H:%M:%S')
                self.conn_var.set(f"客户端: {addr} (连接时间: {start_time})")
            else:
                self.conn_var.set("无客户端连接")
                
            self.root.after(1000, self.update_gui_status)

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='简化VNC代理服务器')
    parser.add_argument('--vnc-host', default='127.0.0.1', help='VNC服务器地址')
    parser.add_argument('--vnc-port', type=int, default=5900, help='VNC服务器端口')
    parser.add_argument('--proxy-port', type=int, default=5901, help='代理服务器端口')
    parser.add_argument('--no-gui', action='store_true', help='不启动GUI界面')
    
    args = parser.parse_args()
    
    proxy = SimpleVNCProxy(args.vnc_host, args.vnc_port, args.proxy_port)
    
    if args.no_gui:
        try:
            proxy.start_server()
        except KeyboardInterrupt:
            logger.info("收到中断信号，停止服务器...")
            proxy.stop_server()
    else:
        proxy.start_gui()

if __name__ == "__main__":
    main()