import os
import sys
import platform
import subprocess
from pathlib import Path

def create_windows_shortcut(target, arguments, icon, shortcut_path, working_dir):
    """
    Creates a Windows shortcut (.lnk) using a temporary VBScript.
    This avoids needing external dependencies like winshell or pywin32.
    """
    vbs_script = f"""
    Set oWS = WScript.CreateObject("WScript.Shell")
    sLinkFile = "{shortcut_path}"
    Set oLink = oWS.CreateShortcut(sLinkFile)
    oLink.TargetPath = "{target}"
    oLink.Arguments = "{arguments}"
    oLink.IconLocation = "{icon}"
    oLink.WorkingDirectory = "{working_dir}"
    oLink.Save
    """
    
    vbs_path = Path(working_dir) / "create_shortcut.vbs"
    try:
        with open(vbs_path, "w", encoding="utf-8") as vbs:
            vbs.write(vbs_script)
        
        subprocess.run(["cscript", "//Nologo", str(vbs_path)], check=True)
        print(f"Atalho criado com sucesso em: {shortcut_path}")
    except Exception as e:
        print(f"Erro ao criar atalho via VBS: {e}")
        # Fallback para .bat simples (menos elegante, mas funciona)
        bat_path = str(shortcut_path).replace(".lnk", ".bat")
        with open(bat_path, "w", encoding="utf-8") as bat:
            bat.write(f'@echo off\ncd /d "{working_dir}"\nstart "" "{target}" {arguments}')
        print(f"Fallback: Criado arquivo .bat em {bat_path}")
    finally:
        if vbs_path.exists():
            os.remove(vbs_path)

def create_linux_desktop_file(target, arguments, icon, working_dir):
    """
    Creates a .desktop file for Linux (Gnome/Unity).
    """
    desktop_entry = f"""[Desktop Entry]
Version=1.0
Name=iBirder
Comment=Identificador de Aves
Exec={target} {arguments}
Icon={icon}
Path={working_dir}
Terminal=false
Type=Application
Categories=Utility;Science;
"""
    
    # Path padrão para aplicações do usuário
    apps_dir = Path.home() / ".local" / "share" / "applications"
    if not apps_dir.exists():
        apps_dir.mkdir(parents=True, exist_ok=True)
        
    desktop_path = apps_dir / "ibirder.desktop"
    
    try:
        with open(desktop_path, "w", encoding="utf-8") as f:
            f.write(desktop_entry)
        
        # Torna executável
        os.chmod(desktop_path, 0o755)
        print(f"Arquivo .desktop criado em: {desktop_path}")
        
    except Exception as e:
        print(f"Erro ao criar .desktop: {e}")

def main():
    sistema = platform.system()
    base_path = Path(__file__).parent.absolute()
    
    print(f"Detectando ambiente: {sistema}")
    
    if sistema == "Windows":
        # Caminhos Windows
        # pythonw.exe no venv para não abrir janela de terminal
        python_exe = base_path / ".venv" / "Scripts" / "pythonw.exe"
        
        # Se não achar no venv, tenta o sys.executable (mas pode abrir terminal se for python.exe)
        if not python_exe.exists():
            python_exe = Path(sys.executable)
            # Tenta achar o pythonw vizinho
            possible_pythonw = python_exe.parent / "pythonw.exe"
            if possible_pythonw.exists():
                python_exe = possible_pythonw

        script_main = base_path / "main.py"
        icon_path = base_path / "assets" / "logo_ave.png"
        
        # Desktop do Usuário
        desktop = Path(os.environ["USERPROFILE"]) / "Desktop"
        shortcut_dest = desktop / "iBirder.lnk"
        
        create_windows_shortcut(
            target=str(python_exe),
            arguments=f'"{str(script_main)}"',
            icon=str(icon_path),
            shortcut_path=str(shortcut_dest),
            working_dir=str(base_path)
        )
        
    elif sistema == "Linux":
        # Caminhos Linux
        python_exe = base_path / ".venv" / "bin" / "python3"
        if not python_exe.exists():
             python_exe = Path(sys.executable)
             
        script_main = base_path / "main.py"
        icon_path = base_path / "assets" / "logo_ave.png"
        
        create_linux_desktop_file(
            target=str(python_exe),
            arguments=str(script_main),
            icon=str(icon_path),
            working_dir=str(base_path)
        )
        
    else:
        print("Sistema operacional não suportado automaticamente para atalhos.")
        return

    print("-" * 30)
    print("Pronto! O ícone do iBirder agora está pronto para uso.")
    print("-" * 30)

if __name__ == "__main__":
    main()
