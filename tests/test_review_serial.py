"""Host-test actual firmware serial receiver with an Arduino shim."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SerialReceiverTests(unittest.TestCase):
    def test_control_bytes_and_bounded_drain(self):
        compiler = shutil.which('c++')
        if not compiler:
            self.skipTest('C++ compiler unavailable')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'Arduino.h').write_text(r'''
#pragma once
#include <string>
#include <cstdio>
#include <cstdint>
#include <sstream>
struct SerialMock {
  std::string input, output;
  size_t position = 0;
  void begin(int) {}
  bool available() { return position < input.size(); }
  char read() { return input[position++]; }
  template<class T> void print(T value) { std::ostringstream s; s << value; output += s.str(); }
  void print(float value, int) { print(value); }
  void println(char value) { print(value); output += '\n'; }
  void println(const char* value) { print(value); output += '\n'; }
  template<class... T> void printf(const char* fmt, T... args) {
    char text[2048]; std::snprintf(text, sizeof(text), fmt, args...); output += text;
  }
} Serial;
struct EspMock {
  uint64_t getEfuseMac() { return 1; }
  unsigned getFreeHeap() { return 100000; }
} ESP;
inline unsigned esp_random() { return 1; }
inline unsigned micros() { return 1; }
inline void delay(int) {}
''')
            (root/'test.cpp').write_text('#include <cassert>\n#include "'+str(ROOT/'esp32/ml_integration/src/main.cpp')+'"\n'+r'''
void receive(const std::string& text) {
  Serial.input = text; Serial.position = 0; Serial.output.clear();
  used = 0; overflow = false;
  while (Serial.available()) loop();
}
int main() {
  self_test_passed = true;
  receive(std::string("RESET\0ignored\n", 14));
  assert(Serial.output.find("LINE_TOO_LONG") != std::string::npos);
  assert(Serial.output.find("reset") == std::string::npos);
  receive("RESET\n");
  assert(Serial.output.find("reset") != std::string::npos);
  receive("1767225600,20,60,1000,nan,50,2\n");
  assert(Serial.output.find("INVALID_CSV") != std::string::npos);
  receive(std::string(1000, 'x')+"\n");
  assert(Serial.output.find("LINE_TOO_LONG") != std::string::npos);
  Serial.input = std::string(1000, 'x'); Serial.position = 0;
  used = 0; overflow = false;
  loop();
  assert(Serial.position == 256);
}
''')
            subprocess.run([compiler, '-std=c++17', '-O2', '-I'+str(root),
                '-I'+str(ROOT/'esp32/ml_integration/include'),
                '-I'+str(ROOT/'ml/models/uci_beijing_6h/esp32_student/export'),
                '-I'+str(ROOT/'ml/models/uci_beijing_event_rules_6sensor/esp32_student/export'),
                str(root/'test.cpp'), '-o', str(root/'test')], check=True, capture_output=True)
            subprocess.run([str(root/'test')], check=True, capture_output=True)
