#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import logging
import requests
from typing import Dict, List, Optional, Any, Union

logger = logging.getLogger(__name__)

class GrafanaDashboardManager:
    """Grafana仪表盘管理类，负责加载和提供Grafana仪表盘配置"""
    
    def __init__(self, dashboard_dir: str = None):
        """
        初始化Grafana仪表盘管理器
        
        Args:
            dashboard_dir: Grafana仪表盘JSON文件所在目录
        """
        if dashboard_dir is None:
            # 默认使用当前文件所在目录
            current_dir = os.path.dirname(os.path.abspath(__file__))
            self.dashboard_dir = current_dir
        else:
            self.dashboard_dir = dashboard_dir
            
        self.dashboards = {}
        self.grafana_url = os.getenv('GRAFANA_URL', 'http://localhost:3000')
        self._load_dashboards()
    
    def _load_dashboards(self) -> None:
        """加载目录中的所有仪表盘JSON文件"""
        try:
            # 查找目录中所有.json文件
            for filename in os.listdir(self.dashboard_dir):
                if filename.endswith('.json'):
                    file_path = os.path.join(self.dashboard_dir, filename)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            dashboard_config = json.load(f)
                            
                            # 提取仪表盘UID作为键
                            if 'uid' in dashboard_config:
                                dashboard_uid = dashboard_config['uid']
                                dashboard_title = dashboard_config.get('title', '未命名仪表盘')
                                
                                self.dashboards[dashboard_uid] = {
                                    'uid': dashboard_uid,
                                    'title': dashboard_title,
                                    'config': dashboard_config,
                                    'filename': filename
                                }
                                logger.info(f"已加载仪表盘: {dashboard_title} (UID: {dashboard_uid})")
                            else:
                                logger.warning(f"跳过仪表盘文件 {filename}: 缺少UID字段")
                    except Exception as e:
                        logger.error(f"加载仪表盘文件 {filename} 失败: {str(e)}")
        except Exception as e:
            logger.error(f"加载仪表盘目录失败: {str(e)}")
    
    def get_dashboard_list(self) -> List[Dict[str, str]]:
        """
        获取所有可用仪表盘的列表
        
        Returns:
            包含仪表盘基本信息的字典列表
        """
        return [
            {
                'uid': dashboard['uid'],
                'title': dashboard['title'],
                'url': f"/d/{dashboard['uid']}"
            }
            for dashboard in self.dashboards.values()
        ]
    
    def get_dashboard_config(self, dashboard_uid: str) -> Optional[Dict[str, Any]]:
        """
        获取指定仪表盘的完整配置
        
        Args:
            dashboard_uid: 仪表盘UID
            
        Returns:
            仪表盘配置字典，如果不存在则返回None
        """
        if dashboard_uid in self.dashboards:
            return self.dashboards[dashboard_uid]['config']
        return None
    
    def get_embed_url(self, dashboard_uid: str, device_id: str = None) -> Optional[str]:
        """
        获取仪表盘的嵌入URL
        
        Args:
            dashboard_uid: 仪表盘UID
            device_id: 设备ID，用于过滤数据
            
        Returns:
            嵌入URL，如果不存在则返回None
        """
        if dashboard_uid not in self.dashboards:
            return None
            
        grafana_url = os.getenv('GRAFANA_URL', 'http://localhost:3000')
        embed_url = f"{grafana_url}/d/{dashboard_uid}?orgId=1&kiosk"
        
        # 添加模板变量参数
        if device_id:
            embed_url += f"&var-device_id={device_id}"
            
        return embed_url
    
    def get_dashboard_by_tag(self, tag: str) -> List[Dict[str, str]]:
        """
        按标签筛选仪表盘
        
        Args:
            tag: 要筛选的标签
            
        Returns:
            匹配标签的仪表盘列表
        """
        matched_dashboards = []
        for dashboard in self.dashboards.values():
            config = dashboard['config']
            if 'tags' in config and tag in config['tags']:
                matched_dashboards.append({
                    'uid': dashboard['uid'],
                    'title': dashboard['title'],
                    'url': f"/d/{dashboard['uid']}"
                })
        return matched_dashboards
    
    def get_template_variables(self, dashboard_uid: str) -> Dict[str, Any]:
        """
        获取指定仪表盘的模板变量
        
        Args:
            dashboard_uid: 仪表盘UID
            
        Returns:
            模板变量字典，如果不存在则返回空字典
        """
        if dashboard_uid in self.dashboards:
            config = self.dashboards[dashboard_uid]['config']
            if 'templating' in config and 'list' in config['templating']:
                variables = {}
                for var in config['templating']['list']:
                    var_name = var.get('name')
                    if var_name:
                        var_value = var.get('current', {}).get('value')
                        variables[var_name] = var_value
                return variables
        return {}
    
    def reload_dashboards(self) -> None:
        """重新加载所有仪表盘配置"""
        self.dashboards = {}
        self._load_dashboards()
        
    @property
    def dashboard_count(self) -> int:
        """获取仪表盘总数"""
        return len(self.dashboards)

    def import_dashboards_to_grafana(self):
        """
        将本地仪表盘配置导入到Grafana实例
        """
        try:
            # 检查Grafana是否可访问
            try:
                response = requests.get(f"{self.grafana_url}/api/health")
                if response.status_code != 200:
                    logger.error(f"Grafana服务不可用: {response.status_code}")
                    return False
            except Exception as e:
                logger.error(f"无法连接到Grafana: {e}")
                return False
                
            # 导入所有仪表盘
            for uid, dashboard in self.dashboards.items():
                # 准备导入数据
                import_data = {
                    "dashboard": dashboard["config"],
                    "overwrite": True,
                    "folderId": 0,  # 放在General文件夹
                }
                
                # 发送导入请求
                try:
                    headers = {'Content-Type': 'application/json'}
                    response = requests.post(
                        f"{self.grafana_url}/api/dashboards/db",
                        json=import_data,
                        headers=headers
                    )
                    
                    if response.status_code in (200, 201):
                        logger.info(f"成功导入仪表盘 {dashboard['title']} (UID: {uid})")
                    else:
                        logger.warning(f"导入仪表盘 {dashboard['title']} 失败: {response.status_code} - {response.text}")
                except Exception as e:
                    logger.error(f"导入仪表盘 {dashboard['title']} 时出错: {e}")
            
            return True
        except Exception as e:
            logger.error(f"导入仪表盘到Grafana时发生错误: {e}")
            return False


# 单例实例
dashboard_manager = GrafanaDashboardManager()

def get_dashboard_manager() -> GrafanaDashboardManager:
    """获取仪表盘管理器实例"""
    return dashboard_manager 