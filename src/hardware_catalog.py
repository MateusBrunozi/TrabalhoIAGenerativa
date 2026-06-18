"""
hardware_catalog.py  –  Catálogo de hardware suportado pelo assistente.

Estrutura:
  CATALOG = {
    "CHAVE_MARCA": {
      "label":     texto exibido no botão
      "emoji":     ícone
      "tipo":      "desktop" | "notebook"
      "genericos": lista de palavras-chave que identificam manuais
                   GENÉRICOS da marca (Q-LED, POST codes, troubleshooting
                   geral) — usados como contexto extra quando o manual
                   específico do modelo não cobre o sintoma perguntado.
      "modelos": {
        "CHAVE_MODELO": {
          "label":    texto exibido no botão
          "desc":     descrição curta (exibida na confirmação)
          "filtro":   lista de palavras-chave usadas no filtro RAG
                      (devem TODAS aparecer no nome do arquivo)
        }
      }
    }
  }

Para adicionar novos modelos/marcas basta editar este arquivo.
"""

CATALOG: dict = {

    # ══════════════════════════════════════════════════════
    #  PLACAS-MÃE DESKTOP
    # ══════════════════════════════════════════════════════

    "ASUS": {
        "label": "ASUS",
        "emoji": "🔵",
        "tipo":  "desktop",
        # Pasta data/manuals/asus/genericos/ → Asus_qled.pdf, ManualGenericoAsus.pdf, POSTCODES.pdf
        # "asus" cobre os dois primeiros; "post" e "codes" cobrem o terceiro mesmo sem "asus" no nome.
        "genericos": ["qled", "post", "postcodes", "codes", "generico", "genericoasus", "qled", "manualgenerico"],
        "modelos": {
            "ASUS_PRIME_A520":  {"label": "PRIME A520M-E/K",          "desc": "ASUS PRIME A520 (AMD AM4)",            "filtro": ["asus", "prime", "a520"]},
            "ASUS_TUF_A520":    {"label": "TUF Gaming A520M-PLUS",    "desc": "ASUS TUF Gaming A520 (AMD AM4)",       "filtro": ["asus", "tuf", "a520"]},
            "ASUS_PRIME_B450":  {"label": "PRIME B450M-A II",         "desc": "ASUS PRIME B450 (AMD AM4)",            "filtro": ["asus", "prime", "b450"]},
            "ASUS_TUF_B450":    {"label": "TUF Gaming B450M-Plus II", "desc": "ASUS TUF Gaming B450 (AMD AM4)",       "filtro": ["asus", "tuf", "b450"]},
            "ASUS_ROG_B550":    {"label": "ROG STRIX B550-F/E/G",     "desc": "ASUS ROG STRIX B550 (AMD AM4)",        "filtro": ["asus", "rog", "b550"]},
            "ASUS_TUF_B550":    {"label": "TUF Gaming B550-Plus",     "desc": "ASUS TUF Gaming B550  (AMD AM4)",      "filtro": ["asus", "tuf", "b550"]},
            "ASUS_PRIME_B550":  {"label": "PRIME B550M/B550-Plus",    "desc": "ASUS PRIME B550  (AMD AM4)",           "filtro": ["asus", "prime", "b550"]},
            "ASUS_ROG_Z690":    {"label": "ROG STRIX Z690-F/E",       "desc": "ASUS ROG STRIX Z690  (Intel LGA1700)", "filtro": ["asus", "rog", "z690"]},
            "ASUS_TUF_Z690":    {"label": "TUF Gaming Z690-Plus",     "desc": "ASUS TUF Gaming Z690  (Intel LGA1700)","filtro": ["asus", "tuf", "z690"]},
            "ASUS_PRIME_Z690":  {"label": "PRIME Z690-P/A",           "desc": "ASUS PRIME Z690  (Intel LGA1700)",     "filtro": ["asus", "prime", "z690"]},
            "ASUS_ROG_Z790":    {"label": "ROG STRIX Z790-F/E",       "desc": "ASUS ROG STRIX Z790  (Intel LGA1700)", "filtro": ["asus", "rog", "z790"]},
            "ASUS_TUF_Z790":    {"label": "TUF Gaming Z790-Plus",     "desc": "ASUS TUF Gaming Z790  (Intel LGA1700)","filtro": ["asus", "tuf", "z790"]},
        },
    },

    "MSI": {
        "label": "MSI",
        "emoji": "🔴",
        "tipo":  "desktop",
        "genericos": ["ezdebug", "ez_debug", "post", "generico", "codes", "postcodes", "manualgenerico", "guide"],
        "modelos": {
            "MSI_A520_PRO":      {"label": "A520M-A PRO",          "desc": "MSI A520M-A PRO (AMD AM4)",             "filtro": ["msi", "a520", "pro"]},
            "MSI_MAG_A520":      {"label": "MAG A520M Vector",     "desc": "MSI MAG A520 (AMD AM4)",                "filtro": ["msi", "a520", "mag"]},
            "MSI_B450_TOMAHAWK": {"label": "B450 Tomahawk MAX",    "desc": "MSI B450 Tomahawk (AMD AM4)",           "filtro": ["msi", "b450", "tomahawk"]},
            "MSI_B450_PRO":      {"label": "B450M PRO-VDH MAX",    "desc": "MSI B450 PRO (AMD AM4)",                "filtro": ["msi", "b450", "pro"]},
            "MSI_B550_TOMAHAWK": {"label": "MAG B550 Tomahawk",    "desc": "MSI MAG B550 Tomahawk  (AMD AM4)",      "filtro": ["msi", "b550", "tomahawk"]},
            "MSI_X570_EDGE":     {"label": "MPG X570 Gaming Edge", "desc": "MSI X570 Gaming Edge  (AMD AM4)",       "filtro": ["msi", "x570", "edge"]},
            "MSI_Z690_TOMAHAWK": {"label": "MAG Z690 Tomahawk",    "desc": "MSI MAG Z690 Tomahawk  (Intel LGA1700)","filtro": ["msi", "z690", "tomahawk"]},
            "MSI_Z690_EDGE":     {"label": "MPG Z690 Gaming Edge", "desc": "MSI MPG Z690 Gaming Edge  (Intel LGA1700)","filtro": ["msi", "z690", "edge"]},
            "MSI_Z790_TOMAHAWK": {"label": "MAG Z790 Tomahawk",    "desc": "MSI MAG Z790 Tomahawk  (Intel LGA1700)","filtro": ["msi", "z790", "tomahawk"]},
            "MSI_Z790_EDGE":     {"label": "MPG Z790 Gaming Edge", "desc": "MSI MPG Z790 Gaming Edge  (Intel LGA1700)","filtro": ["msi", "z790", "edge"]},
        },
    },

    "GIGABYTE": {
        "label": "Gigabyte",
        "emoji": "🟠",
        "tipo":  "desktop",
        "genericos": ["post", "codes", "generico", "led", "qled", "postcodes", "manualgenerico", "guide"],
        "modelos": {
            "GB_A520_DS3H":     {"label": "A520M DS3H",              "desc": "Gigabyte A520M DS3H (AMD AM4)",        "filtro": ["gigabyte", "a520", "ds3h"]},
            "GB_A520_AORUS":    {"label": "A520 AORUS Elite",        "desc": "Gigabyte A520 AORUS (AMD AM4)",        "filtro": ["gigabyte", "a520", "aorus"]},
            "GB_B450_DS3H":     {"label": "B450M DS3H",               "desc": "Gigabyte B450M DS3H (AMD AM4)",       "filtro": ["gigabyte", "b450", "ds3h"]},
            "GB_B450_AORUS":    {"label": "B450 AORUS M",             "desc": "Gigabyte B450 AORUS (AMD AM4)",       "filtro": ["gigabyte", "b450", "aorus"]},
            "GIGA_B550_AORUS":  {"label": "B550 AORUS Pro/Elite",     "desc": "Gigabyte B550 AORUS  (AMD AM4)",      "filtro": ["gigabyte", "b550", "aorus"]},
            "GIGA_B550_GAMING": {"label": "B550 Gaming X/V2",         "desc": "Gigabyte B550 Gaming X  (AMD AM4)",   "filtro": ["gigabyte", "b550", "gaming"]},
            "GIGA_X570_AORUS":  {"label": "X570 AORUS Master/Elite",  "desc": "Gigabyte X570 AORUS  (AMD AM4)",      "filtro": ["gigabyte", "x570", "aorus"]},
            "GIGA_Z690_AORUS":  {"label": "Z690 AORUS Master/Elite",  "desc": "Gigabyte Z690 AORUS  (Intel LGA1700)","filtro": ["gigabyte", "z690", "aorus"]},
            "GIGA_Z690_GAMING": {"label": "Z690 Gaming X DDR4/DDR5",  "desc": "Gigabyte Z690 Gaming X  (Intel LGA1700)","filtro": ["gigabyte", "z690", "gaming"]},
            "GIGA_Z790_AORUS":  {"label": "Z790 AORUS Master/Elite",  "desc": "Gigabyte Z790 AORUS  (Intel LGA1700)","filtro": ["gigabyte", "z790", "aorus"]},
        },
    },

    # ══════════════════════════════════════════════════════
    #  NOTEBOOKS
    # ══════════════════════════════════════════════════════

    "DELL": {
        "label": "Dell",
        "emoji": "💻",
        "tipo":  "notebook",
        "genericos": ["dell", "service", "troubleshooting"],
        "modelos": {
            "DELL_INSPIRON_15": {"label": "Inspiron 15 (3000/5000)", "desc": "Dell Inspiron 15  (série 3000/5000)", "filtro": ["dell", "inspiron", "15"]},
            "DELL_INSPIRON_14": {"label": "Inspiron 14 (5000/7000)", "desc": "Dell Inspiron 14  (série 5000/7000)", "filtro": ["dell", "inspiron", "14"]},
        },
    },
}

# ── Helpers ──────────────────────────────────────────────────────────────────

def get_marcas() -> list[tuple[str, str]]:
    """Retorna lista de (chave, label_com_emoji) para montar botões."""
    return [
        (chave, f"{dados['emoji']} {dados['label']}")
        for chave, dados in CATALOG.items()
    ]

def get_modelos(marca: str) -> list[tuple[str, str]]:
    """Retorna lista de (chave_modelo, label) para a marca especificada."""
    if marca not in CATALOG:
        return []
    return [
        (chave, dados["label"])
        for chave, dados in CATALOG[marca]["modelos"].items()
    ]

def get_modelo_info(marca: str, modelo: str) -> dict | None:
    """Retorna o dict completo de um modelo específico."""
    return CATALOG.get(marca, {}).get("modelos", {}).get(modelo)

def get_filtro_rag(marca: str, modelo: str) -> list[str]:
    """Retorna as palavras-chave de filtro RAG (manual específico) de um modelo."""
    info = get_modelo_info(marca, modelo)
    return info.get("filtro", []) if info else []

def get_genericos_marca(marca: str) -> list[str]:
    """Retorna as palavras-chave que identificam manuais genéricos da marca."""
    return CATALOG.get(marca, {}).get("genericos", [])
