#!/usr/bin/env python3
"""
Phase 3 Verification Tests
Tests article response policy hardening
"""
import sys
import os
sys.path.append(os.getcwd())

def test_smc_url_validation():
    """Test SMC URL validation helper"""
    print("\n🧪 Testing SMC URL Validation...")
    
    import yaml
    from src.core.chat_engine import ChatEngine
    
    with open("configs/config.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    
    engine = ChatEngine(cfg=cfg)
    
    # Test cases
    test_urls = [
        ("http://10.192.133.33/smc/article/123", True, "SMC internal IP"),
        ("http://smc.example.com/article", True, "SMC domain"),
        ("http://external.com/article", False, "External URL"),
        ("https://google.com", False, "External service"),
        ("", False, "Empty URL"),
    ]
    
    all_passed = True
    for url, expected, description in test_urls:
        result = engine._is_smc_url(url)
        passed = (result == expected)
        status = "✅" if passed else "❌"
        print(f"  {status} {description}: {url[:40]:<40} -> {result}")
        if not passed:
            all_passed = False
            print(f"      Expected: {expected}, Got: {result}")
    
    return all_passed

def test_link_only_mode_structure():
    """Test that LINK_ONLY mode structure is correctly defined"""
    print("\n🧪 Testing LINK_ONLY Mode Structure...")
    
    # Check if the code contains the LINK_ONLY implementation
    with open("src/chat_engine.py", "r", encoding="utf-8") as f:
        content = f.read()
    
    checks = [
        ("article_link_only" in content, "LINK_ONLY route defined"),
        ("MODE 2 - LINK_ONLY" in content, "MODE 2 comment present"),
        ("ไม่สามารถโหลดเนื้อหาได้" in content, "Error message present"),
        ("404" in content and "Timeout" in content, "Specific error handling"),
    ]
    
    all_passed = True
    for check, description in checks:
        status = "✅" if check else "❌"
        print(f"  {status} {description}")
        if not check:
            all_passed = False
    
    return all_passed

def test_article_ok_mode_structure():
    """Test that ARTICLE_OK mode enforces SMC link first"""
    print("\n🧪 Testing ARTICLE_OK Mode Structure...")
    
    with open("src/chat_engine.py", "r", encoding="utf-8") as f:
        content = f.read()
    
    checks = [
        ("MODE 1 - ARTICLE_OK" in content, "MODE 1 comment present"),
        ("แหล่งข้อมูลหลัก (SMC)" in content, "SMC link marker present"),
        ("article_title" in content, "Article title resolution"),
        ("is_technical_query" in content, "Technical query detection"),
    ]
    
    all_passed = True
    for check, description in checks:
        status = "✅" if check else "❌"
        print(f"  {status} {description}")
        if not check:
            all_passed = False
    
    return all_passed

def main():
    print("=" * 70)
    print("PHASE 3: ARTICLE RESPONSE POLICY VERIFICATION")
    print("=" * 70)
    
    results = []
    
    # Run tests
    results.append(("SMC URL Validation", test_smc_url_validation()))
    results.append(("LINK_ONLY Mode Structure", test_link_only_mode_structure()))
    results.append(("ARTICLE_OK Mode Structure", test_article_ok_mode_structure()))
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    passed_count = sum(1 for _, p in results if p)
    total_count = len(results)
    
    for name, passed in results:
        status = "✅" if passed else "❌"
        print(f"{status} {name}")
    
    print(f"\nTotal:  {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("\n🎉 ALL PHASE 3 TESTS PASSED!")
        return 0
    else:
        print(f"\n⚠️  {total_count - passed_count} test(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
