"""
Template Creator Helper
Quick utility to extract templates from videos with resolution-agnostic coordinates
"""

import sys
from pathlib import Path
from detectors import TemplateDetector


def main():
    print("=" * 70)
    print("Template Creator - Auto-Editor v2.0 (Resolution-Agnostic)")
    print("=" * 70)
    
    if len(sys.argv) < 4:
        print("\nUsage:")
        print("  python create_template.py <video> <timestamp> <template_name> [--norm x y w h | --pixels x y w h]")
        print("\nModes:")
        print("  --norm   : Coordenadas normalizadas (0.0-1.0, recomendado)")
        print("  --pixels : Coordenadas absolutas en píxeles")
        print("\nExamples:")
        print("  # Sin región (frame completo):")
        print("  python create_template.py gameplay.mp4 1234 lol_victory")
        print()
        print("  # Con región normalizada (funciona en CUALQUIER resolución):")
        print("  python create_template.py gameplay.mp4 1234 lol_victory --norm 0.395 0.278 0.208 0.185")
        print()
        print("  # Con píxeles absolutos (solo para 1920x1080):")
        print("  python create_template.py gameplay.mp4 1234 lol_victory --pixels 760 300 400 200")
        print("\nRegiones normalizadas comunes:")
        print("  Victory/Defeat (centro-superior): --norm 0.395 0.278 0.208 0.185")
        print("  Centro completo: --norm 0.25 0.25 0.5 0.5")
        print("  Full screen: (omitir región)")
        sys.exit(1)
    
    video_path = sys.argv[1]
    timestamp = float(sys.argv[2])
    template_name = sys.argv[3]
    
    region = None
    normalized = False
    
    if len(sys.argv) >= 9:
        mode = sys.argv[4]
        
        if mode == "--norm":
            normalized = True
            x = float(sys.argv[5])
            y = float(sys.argv[6])
            w = float(sys.argv[7])
            h = float(sys.argv[8])
            region = (x, y, w, h)
            print(f"\n[INFO] Usando región NORMALIZADA: ({x:.3f}, {y:.3f}, {w:.3f}, {h:.3f})")
            print(f"[INFO] Esto funcionará en CUALQUIER resolución automáticamente")
        
        elif mode == "--pixels":
            normalized = False
            x = int(sys.argv[5])
            y = int(sys.argv[6])
            w = int(sys.argv[7])
            h = int(sys.argv[8])
            region = (x, y, w, h)
            print(f"\n[INFO] Usando región en PÍXELES: ({x}, {y}, {w}, {h})")
            print(f"[WARNING] Esto solo funcionará correctamente en la resolución del video")
        
        else:
            print(f"\n[ERROR] Modo desconocido: {mode}")
            print("[ERROR] Usa --norm o --pixels")
            sys.exit(1)
    
    if not Path(video_path).exists():
        print(f"\n[ERROR] Video no encontrado: {video_path}")
        sys.exit(1)
    
    print(f"\n[INFO] Video: {video_path}")
    print(f"[INFO] Timestamp: {timestamp}s")
    print(f"[INFO] Template name: {template_name}")
    
    detector = TemplateDetector()
    
    # Get video resolution
    resolution = detector.get_video_resolution(video_path)
    if resolution:
        print(f"[INFO] Resolución del video: {resolution[0]}x{resolution[1]}")
        
        # If using normalized, show pixel equivalent
        if normalized and region:
            pixel_region = detector.denormalize_region(region, resolution)
            print(f"[INFO] Equivalente en píxeles: ({pixel_region[0]}, {pixel_region[1]}, {pixel_region[2]}, {pixel_region[3]})")
    
    if detector.create_template_from_video(video_path, timestamp, template_name, region, normalized):
        print(f"\n[SUCCESS] ✓ Template creado exitosamente")
        print(f"[SUCCESS] Guardado en: templates/{template_name}.png")
        
        if normalized and region:
            print(f"\n[INFO] Para usar este template, agregalo a config.json:")
            print(f'  "template_regions": {{')
            print(f'    "{template_name}": [{region[0]:.3f}, {region[1]:.3f}, {region[2]:.3f}, {region[3]:.3f}]')
            print(f'  }}')
        else:
            print(f"\n[INFO] Template de frame completo creado")
            print(f"[INFO] Para usar este template, activa en config.json:")
            print(f'  "enable_template_detection": true')
    else:
        print(f"\n[ERROR] No se pudo crear el template")
        sys.exit(1)


if __name__ == "__main__":
    main()
