# AI for Ransomware Detection

## Inicializar proyecto

Iniciar entorno python

```sh
python -m venv venv

source venv/bin/activate
```

### Freezar dependencias

```sh
pip freeze > requirements.txt
```

### Instalar dependencias

```sh
pip install -r requirements.txt
```

### Desactivar entorno

```sh
deactivate
```

#### Como use python 3.11

```sh
echo -e 'export PYENV_ROOT="$HOME/.pyenv"\nexport PATH="$PYENV_ROOT/bin:$PATH"\neval "$(pyenv init --path)"\neval "$(pyenv init -)"\neval "$(pyenv virtualenv-init -)"' >> ~/.zshrc
source ~/.zshrc
pyenv activate tf-env
python --version
```

---

# USTC-TFC2016

[yungshenglu/USTC-TK2016](https://github.com/yungshenglu/USTC-TK2016).

> **NOTICE:** This repository credits to [echowei/DeepTraffic](https://github.com/echowei/DeepTraffic)

## Description

```
Benign/
    ├── BitTorrent.pcap
    ├── Facetime.pcap
    ├── FTP.7z
    ├── Gmail.pcap
    ├── MySQL.pcap
    ├── Outlook.pcap
    ├── Skype.pcap
    ├── SMB.7z
    ├── Weibo.7z
    └── WorldOfWarcraft.pcap
Malware/
    ├── Cridex.7z
    ├── Geodo.7z
    ├── Htbot.7z
    ├── Miuref.pcap
    ├── Neris.7z
    ├── Nsis-ay.7z
    ├── Shifu.7z
    ├── Tinba.pcap
    ├── Virut.7z
    └── Zeus.pcap
```

---

## Contributor

- [Wei Wang](https://github.com/echowei) - ww8137@mail.ustc.edu.cn
- [David Lu](https://github.com/yungshenglu)

---

## License

[Mozilla Public License Version 2.0](LICENSE)
