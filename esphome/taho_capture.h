// Діагностика TAHO для робочої прошивки (generator.yaml): той самий алгоритм taho_rpm.h рахує оберти,
// а поруч записується час кожного фронту на GPIO14 і друкується в лог. Генератор при цьому працює як завжди.
// Підключення: includes taho_rpm.h і taho_capture.h, в on_boot taho_capture::setup() замість taho_rpm::setup().
#pragma once
#include <Arduino.h>
#include "esp_timer.h"
#include "soc/gpio_struct.h"
#include "esphome/core/log.h"

namespace taho_capture {

static const int PIN = 14;
static const int N = 600;  // фронтів (обох напрямків) в одному записі

static volatile uint32_t raw_rising = 0;
static volatile uint32_t ts[N];
static volatile uint8_t lvl[N];
static volatile int n = 0;
static volatile bool armed = false;

static void IRAM_ATTR isr() {
  taho_rpm::isr();  // робочий алгоритм обертів
  uint32_t now = (uint32_t) esp_timer_get_time();
  uint8_t level = (GPIO.in >> PIN) & 1;
  if (level) raw_rising++;
  if (armed && n < N) {
    ts[n] = now;
    lvl[n] = level;
    n++;
    if (n >= N) armed = false;
  }
}

static void setup() {
  pinMode(PIN, INPUT);
  attachInterrupt(digitalPinToInterrupt(PIN), isr, CHANGE);
}

static void arm() {
  if (armed) return;
  n = 0;
  armed = true;
}

static bool ready() { return !armed && n >= N; }

static void hist(const char *title, const uint32_t *v, int cnt, int bin, int bins) {
  static const char *TAG = "taho";
  int h[64] = {0};
  for (int i = 0; i < cnt; i++) {
    int b = v[i] / bin;
    h[b >= bins ? bins : b]++;
  }
  char line[220];
  int pos = snprintf(line, sizeof(line), "%s:", title);
  for (int b = 0; b <= bins; b++) {
    if (!h[b]) continue;
    if (b < bins)
      pos += snprintf(line + pos, sizeof(line) - pos, " %d:%d", b * bin, h[b]);
    else
      pos += snprintf(line + pos, sizeof(line) - pos, " >=%d:%d", bins * bin, h[b]);
    if (pos > 170) {
      ESP_LOGI(TAG, "%s", line);
      pos = snprintf(line, sizeof(line), "%s+:", title);
    }
  }
  ESP_LOGI(TAG, "%s", line);
}

// Друк запису. Рядки "+мкс"/"-мкс": фронт вгору/вниз і час від попереднього фронту.
// Потім гістограми (ключ = нижня межа кошика в мкс): тривалість HIGH (вихід LM393 високий, сигнал TAHO
// низький), тривалість LOW, інтервал між фронтами вгору.
static void dump(const char *label) {
  static const char *TAG = "taho";
  ESP_LOGI(TAG, "==== REC %s: %d фронтів за %u мкс ====", label, N, (unsigned) (ts[N - 1] - ts[0]));
  char line[200];
  int pos = 0;
  for (int i = 1; i < N; i++) {
    pos += snprintf(line + pos, sizeof(line) - pos, "%c%u ", lvl[i] ? '+' : '-', (unsigned) (ts[i] - ts[i - 1]));
    if (i % 20 == 0 || i == N - 1) {
      ESP_LOGI(TAG, "E %s", line);
      pos = 0;
      line[0] = 0;
    }
  }
  static uint32_t hi[N], lo[N], rr[N];
  int nh = 0, nl = 0, nr = 0, last_rise = -1;
  for (int i = 1; i < N; i++) {
    uint32_t d = ts[i] - ts[i - 1];
    if (lvl[i]) lo[nl++] = d;  // фронт вгору закінчує LOW
    else hi[nh++] = d;         // фронт вниз закінчує HIGH
    if (lvl[i]) {
      if (last_rise >= 0) rr[nr++] = ts[i] - ts[last_rise];
      last_rise = i;
    }
  }
  hist("HIGH", hi, nh, 100, 40);
  hist("LOW", lo, nl, 100, 40);
  hist("RISE-RISE", rr, nr, 250, 24);
  ESP_LOGI(TAG, "==== END ====");
}

}  // namespace taho_capture
