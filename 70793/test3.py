import platform
import socket

print("Testing socket.gethostname()...")
print(socket.gethostname()) # 여기서 멈추면 네트워크/DNS 문제

print("Testing platform.win32_ver()...")
print(platform.win32_ver()) # 여기서 멈추면 Windows API/레지스트리 문제yy