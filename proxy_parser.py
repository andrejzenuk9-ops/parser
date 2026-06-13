import aiohttp
import asyncio
from typing import List, Tuple
import re
import socket


class ProxyValidator:
    """Валидатор для проверки прокси на валидность"""
    
    SOCKS4_REGEX = r'^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d{1,5})$'
    SOCKS5_REGEX = r'^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d{1,5})$'
    HTTP_REGEX = r'^(https?://)?(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d{1,5})$'
    
    @staticmethod
    def validate_ip(ip: str) -> bool:
        """Проверяет валидность IP адреса"""
        parts = ip.split('.')
        if len(parts) != 4:
            return False
        try:
            return all(0 <= int(part) <= 255 for part in parts)
        except ValueError:
            return False
    
    @staticmethod
    def validate_port(port: str) -> bool:
        """Проверяет валидность порта"""
        try:
            port_num = int(port)
            return 1 <= port_num <= 65535
        except ValueError:
            return False
    
    @staticmethod
    def validate_socks4(proxy: str) -> bool:
        """Проверяет формат SOCKS4 прокси"""
        match = re.match(ProxyValidator.SOCKS4_REGEX, proxy.strip())
        if not match:
            return False
        ip, port = match.groups()
        return ProxyValidator.validate_ip(ip) and ProxyValidator.validate_port(port)
    
    @staticmethod
    def validate_socks5(proxy: str) -> bool:
        """Проверяет формат SOCKS5 прокси"""
        match = re.match(ProxyValidator.SOCKS5_REGEX, proxy.strip())
        if not match:
            return False
        ip, port = match.groups()
        return ProxyValidator.validate_ip(ip) and ProxyValidator.validate_port(port)
    
    @staticmethod
    def validate_http(proxy: str) -> bool:
        """Проверяет формат HTTP/HTTPS прокси"""
        match = re.match(ProxyValidator.HTTP_REGEX, proxy.strip())
        if not match:
            return False
        groups = match.groups()
        ip = groups[1]
        port = groups[2]
        return ProxyValidator.validate_ip(ip) and ProxyValidator.validate_port(port)
    
    @staticmethod
    async def check_proxy_alive(proxy: str, proxy_type: str = 'http', timeout: int = 5) -> bool:
        """Проверяет доступность прокси"""
        try:
            if proxy_type == 'http' or proxy_type == 'https':
                proxy_url = f'http://{proxy}' if not proxy.startswith('http') else proxy
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        'http://httpbin.org/ip',
                        proxy=proxy_url,
                        timeout=aiohttp.ClientTimeout(total=timeout)
                    ) as resp:
                        return resp.status == 200
            # Для SOCKS4/5 базовая проверка подключения
            elif proxy_type in ['socks4', 'socks5']:
                ip, port = proxy.split(':')
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                result = sock.connect_ex((ip, int(port))) == 0
                sock.close()
                return result
        except Exception as e:
            print(f"Ошибка при проверке прокси {proxy}: {e}")
            return False
        return False


class ProxyParser:
    """Парсер для получения прокси из различных источников"""
    
    # Источники прокси
    SOURCES = {
        'socks4': [
            'https://www.proxy-list.download/api/v1/get?type=socks4',
            'https://api.proxyscrape.com/v2/?request=get&protocol=socks4',
        ],
        'socks5': [
            'https://www.proxy-list.download/api/v1/get?type=socks5',
            'https://api.proxyscrape.com/v2/?request=get&protocol=socks5',
        ],
        'http': [
            'https://www.proxy-list.download/api/v1/get?type=http',
            'https://api.proxyscrape.com/v2/?request=get&protocol=http',
        ],
        'https': [
            'https://www.proxy-list.download/api/v1/get?type=https',
            'https://api.proxyscrape.com/v2/?request=get&protocol=https',
        ],
    }
    
    @staticmethod
    async def fetch_proxies(proxy_type: str, validate: bool = True) -> List[str]:
        """Получает прокси определённого типа из источников"""
        proxies = []
        
        sources = ProxyParser.SOURCES.get(proxy_type.lower(), [])
        
        for source in sources:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(source, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        if resp.status == 200:
                            text = await resp.text()
                            # Парсим прокси из ответа
                            found_proxies = re.findall(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,5}', text)
                            proxies.extend(found_proxies)
            except Exception as e:
                print(f"Ошибка при получении прокси с {source}: {e}")
                continue
        
        # Удаляем дубликаты
        proxies = list(set(proxies))
        
        # Валидируем прокси
        if validate:
            validator = ProxyValidator()
            if proxy_type.lower() == 'socks4':
                proxies = [p for p in proxies if validator.validate_socks4(p)]
            elif proxy_type.lower() == 'socks5':
                proxies = [p for p in proxies if validator.validate_socks5(p)]
            elif proxy_type.lower() in ['http', 'https']:
                proxies = [p for p in proxies if validator.validate_http(p)]
        
        return proxies
    
    @staticmethod
    async def fetch_and_check_proxies(proxy_type: str, max_count: int = 50) -> List[str]:
        """Получает и проверяет живые прокси"""
        proxies = await ProxyParser.fetch_proxies(proxy_type, validate=True)
        
        if not proxies:
            return []
        
        # Берём только нужное количество для проверки
        proxies = proxies[:max_count * 2]
        
        # Проверяем живые прокси
        tasks = [ProxyValidator.check_proxy_alive(p, proxy_type.lower()) for p in proxies]
        results = await asyncio.gather(*tasks)
        
        alive_proxies = [p for p, is_alive in zip(proxies, results) if is_alive]
        
        return alive_proxies[:max_count]
