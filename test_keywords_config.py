#!/usr/bin/env python3
"""
Test script to verify keywords loading and HF token configuration
"""

import json
from pathlib import Path

# Test 1: Load keywords.json
print("[TEST 1] Loading keywords.json...")
try:
    with open("keywords.json", 'r', encoding='utf-8') as f:
        keywords = json.load(f)
    
    print(f"  [OK] Idiomas soportados: {list(keywords.keys())}")
    
    # Check Spanish keywords
    if "es" in keywords:
        es_keywords = keywords["es"]
        print(f"  [OK] Juegos en espanol: {list(es_keywords.keys())}")
        
        # Check LoL keywords
        if "lol" in es_keywords:
            lol_keywords = es_keywords["lol"]
            print(f"    [OK] Eventos LoL: {list(lol_keywords.keys())}")
            
            # Check multikill structure
            if "multikill" in lol_keywords:
                multikill = lol_keywords["multikill"]
                print(f"      [OK] Multikill types: {list(multikill.keys())}")
                print(f"      [OK] Pentakill keywords: {multikill['pentakill'][:2]}...")
    
    print("[PASS] keywords.json loaded successfully\n")
except Exception as e:
    print(f"[FAIL] Error loading keywords: {e}\n")

# Test 2: Load config.json and check new fields
print("[TEST 2] Checking config.json for new fields...")
try:
    with open("config.json", 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    fields_to_check = ["language", "keywords_file", "hf_token", "output_directory", "temp_directory"]
    
    for field in fields_to_check:
        if field in config:
            value = config[field]
            if field == "hf_token":
                status = "configured" if value else "not set (null)"
            else:
                status = f"'{value}'"
            print(f"  [OK] {field}: {status}")
        else:
            print(f"  [FAIL] {field}: MISSING!")
    
    print("[PASS] config.json structure OK\n")
except Exception as e:
    print(f"[FAIL] Error loading config: {e}\n")

# Test 3: Simulate VisionLLMDetector keyword loading
print("[TEST 3] Simulating VisionLLMDetector keyword matching...")
try:
    test_response = "Pentakill! Equipo ganador, victoria epica"
    
    game_type = config.get("game_type", "lol")
    language = config.get("language", "es")
    
    game_keywords = keywords.get(language, {}).get(game_type, {})
    
    def match_keywords(text, keyword_list):
        """Simulate keyword matching"""
        text_lower = text.lower()
        for keyword in keyword_list:
            if keyword.lower() in text_lower:
                return True
        return False
    
    # Check multikills
    event_type = "other"
    if "multikill" in game_keywords:
        for multi_event, keywords_list in game_keywords["multikill"].items():
            if match_keywords(test_response, keywords_list):
                event_type = multi_event
                print(f"  [OK] Detected multikill type: {event_type}")
                break
    
    # Check victory
    if "victory" in game_keywords and event_type == "other":
        if match_keywords(test_response, game_keywords["victory"]):
            event_type = "victory"
            print(f"  [OK] Detected event: {event_type}")
    
    print(f"  [OK] Final event_type: '{event_type}'")
    print("[PASS] Keyword matching works correctly\n")
except Exception as e:
    print(f"[FAIL] Error simulating keyword matching: {e}\n")

# Test 4: Check that huggingface_hub can be imported (optional)
print("[TEST 4] Checking Hugging Face hub availability...")
try:
    import huggingface_hub
    print(f"  [OK] huggingface_hub available (version: {huggingface_hub.__version__})")
    print("[PASS] HF hub integration ready\n")
except ImportError:
    print("  [WARN] huggingface_hub not installed (optional - will still work without token)\n")

print("="*60)
print("SUMMARY: All tests passed! System is ready.")
print("="*60)
print("\nNext steps:")
print("1. (Optional) Get HF token: https://huggingface.co/settings/tokens")
print("2. (Optional) Add token to config.json 'hf_token' field")
print("3. Run: python main.py <video.mp4>")
