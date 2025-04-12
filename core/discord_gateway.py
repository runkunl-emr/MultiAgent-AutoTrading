"""
Discord Gateway API实现 - 通过WebSocket与Discord通信
"""
import json
import logging
import threading
import time
from typing import Dict, Any, Callable, Optional

import websocket
import requests

logger = logging.getLogger(__name__)

class DiscordGateway:
    def __init__(self, token: str, message_callback: Callable[[Dict[str, Any]], None]):
        """
        初始化Discord Gateway客户端
        
        Args:
            token: Discord用户token
            message_callback: 收到消息时的回调函数
        """
        self.token = token
        self.message_callback = message_callback
        self.ws = None
        self.heartbeat_interval = 0
        self.heartbeat_thread = None
        self.last_sequence = None
        self.session_id = None
        self.running = False
        self.reconnect_count = 0
        self.reconnect_max = 20
        
    def start(self):
        """启动Gateway连接"""
        self.running = True
        self.connect()
        
    def stop(self):
        """停止Gateway连接"""
        self.running = False
        if self.ws:
            self.ws.close()
            
    def connect(self):
        """建立WebSocket连接"""
        try:
            gateway_url = self._get_gateway_url()
            if not gateway_url:
                raise Exception("无法获取Gateway URL")
                
            # 创建WebSocket连接
            self.ws = websocket.WebSocketApp(
                f"{gateway_url}/?v=9&encoding=json",
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close
            )
            
            # 运行WebSocket (在新线程中)
            ws_thread = threading.Thread(target=self.ws.run_forever, kwargs={
                'ping_interval': 30,
                'ping_timeout': 10
            })
            ws_thread.daemon = True
            ws_thread.start()
            
        except Exception as e:
            logger.error(f"连接失败: {str(e)}")
            self._schedule_reconnect()
            
    def _get_gateway_url(self) -> Optional[str]:
        """获取Discord Gateway URL"""
        try:
            response = requests.get(
                "https://discord.com/api/v9/gateway",
                headers={"Authorization": self.token}
            )
            if response.status_code == 200:
                return response.json()["url"]
            else:
                logger.error(f"获取Gateway URL失败: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"获取Gateway URL异常: {str(e)}")
            return None
            
    def _on_open(self, ws):
        """处理WebSocket连接打开"""
        logger.info("Discord Gateway连接已打开")
    
    def _on_message(self, ws, message):
        """处理收到的WebSocket消息"""
        try:
            data = json.loads(message)
            op_code = data["op"]
            
            # 更新序列号
            if "s" in data and data["s"] is not None:
                self.last_sequence = data["s"]
            
            # 处理不同操作码
            if op_code == 10:  # Hello
                self.heartbeat_interval = data["d"]["heartbeat_interval"] / 1000
                self._start_heartbeat()
                
                # 尝试恢复会话或发送身份验证
                if self.session_id and self.last_sequence:
                    self._send_resume()
                else:
                    self._send_identify()
                    
            elif op_code == 11:  # Heartbeat ACK
                logger.debug("收到心跳确认")
                
            elif op_code == 0:  # Dispatch
                event_type = data["t"]
                
                # 保存会话ID
                if event_type == "READY":
                    self.session_id = data["d"]["session_id"]
                    self.reconnect_count = 0  # 重置重连计数
                    logger.info(f"成功连接到Discord! 用户: {data['d']['user']['username']}")
                    
                # 处理新消息事件
                elif event_type == "MESSAGE_CREATE":
                    self.message_callback(data["d"])
                    
        except Exception as e:
            logger.error(f"处理WebSocket消息出错: {str(e)}")
    
    def _on_error(self, ws, error):
        """处理WebSocket错误"""
        logger.error(f"WebSocket错误: {str(error)}")
    
    def _on_close(self, ws, close_status_code, close_msg):
        """处理WebSocket连接关闭"""
        logger.warning(f"WebSocket连接关闭: {close_status_code} - {close_msg}")
        if self.running:
            self._schedule_reconnect()
    
    def _schedule_reconnect(self):
        """安排重连"""
        if not self.running:
            return
            
        self.reconnect_count += 1
        if self.reconnect_count > self.reconnect_max:
            logger.error("达到最大重连次数，停止重连")
            return
            
        delay = min(30, 2 ** self.reconnect_count)
        logger.info(f"{delay}秒后尝试重连 ({self.reconnect_count}/{self.reconnect_max})")
        
        threading.Timer(delay, self.connect).start()
    
    def _start_heartbeat(self):
        """启动心跳线程"""
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            return
            
        logger.info(f"启动心跳线程，间隔: {self.heartbeat_interval}秒")
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop)
        self.heartbeat_thread.daemon = True
        self.heartbeat_thread.start()
    
    def _heartbeat_loop(self):
        """心跳循环"""
        while self.running and self.ws and self.ws.sock and self.ws.sock.connected:
            try:
                payload = {
                    "op": 1,  # Heartbeat
                    "d": self.last_sequence
                }
                self.ws.send(json.dumps(payload))
                logger.debug(f"发送心跳: {self.last_sequence}")
                time.sleep(self.heartbeat_interval)
            except Exception as e:
                logger.error(f"心跳发送失败: {str(e)}")
                break
    
    def _send_identify(self):
        """发送身份验证"""
        payload = {
            "op": 2,  # Identify
            "d": {
                "token": self.token,
                "properties": {
                    "$os": "macOS",
                    "$browser": "chrome",
                    "$device": "pc"
                },
                "intents": 513  # GUILDS + GUILD_MESSAGES
            }
        }
        
        logger.info("发送身份验证...")
        self.ws.send(json.dumps(payload))
    
    def _send_resume(self):
        """发送恢复会话请求"""
        payload = {
            "op": 6,  # Resume
            "d": {
                "token": self.token,
                "session_id": self.session_id,
                "seq": self.last_sequence
            }
        }
        
        logger.info(f"尝试恢复会话 (seq: {self.last_sequence})...")
        self.ws.send(json.dumps(payload)) 