"""Apply address bar usability changes after the 1.0.3 overlay."""
from pathlib import Path
import sys
root = Path(sys.argv[1])
for name in ('project/Cargo.toml', 'project/src/ui.html', 'test_ui.py', 'setup.go', 'make_brand.py'):
    p = root / name
    s = p.read_text(encoding='utf-8')
    if '1.0.3' not in s:
        raise RuntimeError(f'Unexpected base version: {name}')
    p.write_text(s.replace('1.0.3', '1.0.4'), encoding='utf-8')
p = root / 'make_brand.py'
s = p.read_text(encoding='utf-8')
assert s.count('0x30000') == 2
p.write_text(s.replace('0x30000','0x40000'),encoding='utf-8')
p = root / 'project/src/ui.html'
s = p.read_text(encoding='utf-8')
anchor = "$('nav').onsubmit="
assert s.count(anchor) == 1
s = s.replace(anchor, """// Select the entire URL on initial focus; subsequent clicks edit normally.
const addressInput=$('address');
addressInput.addEventListener('focus',()=>addressInput.select());
addressInput.addEventListener('mousedown',e=>{
    if(e.button!==0||document.activeElement===addressInput)return;
    e.preventDefault();
    addressInput.focus();
    addressInput.select();
});
""" + anchor)
p.write_text(s, encoding='utf-8')
p = root / 'test_ui.py'
s = p.read_text(encoding='utf-8')
anchor = "    page.locator('#address').fill('test query')"
assert s.count(anchor) == 1
s = s.replace(anchor, """    # Initial click selects all; second click moves caret; state refresh preserves edits.
    address = page.locator('#address')
    address.evaluate('e=>e.blur()')
    render(url='https://www.naver.com/')
    address.click()
    assert address.evaluate('e=>[e.selectionStart,e.selectionEnd]') == [0,len(address.input_value())]
    address.click(position={'x':35,'y':10})
    assert address.evaluate('e=>e.selectionStart===e.selectionEnd')
    address.evaluate('e=>e.blur()')
    address.click()
    page.keyboard.type('example.com')
    assert address.input_value()=='example.com'
    render(notice='refresh while editing')
    assert address.input_value()=='example.com'
    page.keyboard.press('Control+l')
    assert address.evaluate('e=>[e.selectionStart,e.selectionEnd]') == [0,len(address.input_value())]
""" + anchor)
p.write_text(s, encoding='utf-8')
