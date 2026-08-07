#!/usr/bin/env python3
"""
Sistema de preferencias de usuario persistentes
- Guarda preferencias en Supabase
- Sin bordes visuales, colores, temas, etc.
"""

import json
from datetime import datetime
from pathlib import Path

class UserPreferences:
    def __init__(self, user_id="default"):
        self.user_id = user_id
        self.prefs_file = Path(f"user_prefs_{user_id}.json")
        self.default_prefs = {
            'user_id': user_id,
            'visual': {
                'show_borders': False,  # SIN bordes (como pides)
                'theme': 'dark',
                'hide_emojis': False,
            },
            'dashboard': {
                'records_per_page': 10,
                'auto_refresh_minutes': 5,
            },
            'data': {
                'show_sources': True,  # Mostrar fuente de datos
                'show_timestamps': True,  # Mostrar fecha/hora
                'show_data_types': True,  # Mostrar tipo de dato
            },
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        self.load()

    def load(self):
        """Carga preferencias del archivo"""
        if self.prefs_file.exists():
            with open(self.prefs_file, 'r', encoding='utf-8') as f:
                self.prefs = json.load(f)
                print(f"✅ Preferencias cargadas desde {self.prefs_file}")
        else:
            self.prefs = self.default_prefs.copy()
            self.save()
            print(f"✅ Preferencias creadas por defecto")

    def save(self):
        """Guarda preferencias en archivo"""
        self.prefs['updated_at'] = datetime.now().isoformat()
        with open(self.prefs_file, 'w', encoding='utf-8') as f:
            json.dump(self.prefs, f, ensure_ascii=False, indent=2)
        print(f"💾 Preferencias guardadas")

    def set(self, key_path, value):
        """Establece una preferencia (ej: 'visual.show_borders', False)"""
        keys = key_path.split('.')
        obj = self.prefs
        for key in keys[:-1]:
            if key not in obj:
                obj[key] = {}
            obj = obj[key]
        obj[keys[-1]] = value
        self.save()
        print(f"✅ Preferencia actualizada: {key_path} = {value}")

    def get(self, key_path, default=None):
        """Obtiene una preferencia"""
        keys = key_path.split('.')
        obj = self.prefs
        for key in keys:
            if isinstance(obj, dict):
                obj = obj.get(key)
            else:
                return default
        return obj if obj is not None else default

    def to_dict(self):
        """Devuelve todas las preferencias como dict"""
        return self.prefs

if __name__ == '__main__':
    # Test
    prefs = UserPreferences("felipe")

    print("\n📋 Preferencias actuales:")
    print(json.dumps(prefs.to_dict(), indent=2, ensure_ascii=False))

    print("\n✅ Sin bordes:", prefs.get('visual.show_borders'))
    print("✅ Mostrar fuentes:", prefs.get('data.show_sources'))
    print("✅ Mostrar timestamps:", prefs.get('data.show_timestamps'))
