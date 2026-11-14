// Діагностика TAHO: записує час кожного фронту на GPIO14 (вихід LM393) і рахує оберти.
// Підключається з genset_diag.yaml через esphome: includes. Тимчасова прошивка, не для постійної роботи.
#pragma once
#include <Arduino.h>
#include "esp_timer.h"
#include "soc/gpio_struct.h"

namespace taho_diag {

static const int PIN = 14;
static const uint32_t FILTER_US = 1800;  // той самий фільтр, що й у pulse_meter робочої прошивки
static const int N = 400;                // фронтів (обох напрямків) в одному записі, ~0,2-0,4 с

static volatile uint32_t raw_rising = 0;   // усі фронти вгору
static volatile uint32_t filt_rising = 0;  // фронти вгору, що пройшли фільтр 1,8 мс
static volatile uint32_t last_valid_us = 0;

static volatile uint32_t ts[N];
static volatile uint8_t lvl[N];
static volatile int n = 0;
static volatile bool armed = false;

static void IRAM_ATTR isr() {
  uint32_t now = (uint32_t) esp_timer_get_time();
  uint8_t level = (GPIO.in >> PIN) & 1;
  if (level) {
    raw_rising++;
    if ((uint32_t) (now - last_valid_us) >= FILTER_US) {
      last_valid_us = now;
      filt_rising++;
    }
  }
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

// Друк запису: послідовність інтервалів між сусідніми фронтами в мкс.
// "+" — фронт вгору (вихід LM393 став HIGH), "-" — фронт вниз. Число = мкс від попереднього фронту.
// Потім гістограма інтервалів між фронтами вгору (кошики по 250 мкс).
static void dump(const char *label) {
  static const char *TAG = "taho";
  ESP_LOGI(TAG, "==== Запис %s: %d фронтів за %u мкс ====", label, N, (unsigned) (ts[N - 1] - ts[0]));
  char line[200];
  int pos = 0;
  for (int i = 1; i < N; i++) {
    pos += snprintf(line + pos, sizeof(line) - pos, "%c%u ", lvl[i] ? '+' : '-', (unsigned) (ts[i] - ts[i - 1]));
    if (i % 20 == 0 || i == N - 1) {
      ESP_LOGI(TAG, "%s", line);
      pos = 0;
      line[0] = 0;
    }
  }
  static const int B = 24;  // 0..6000 мкс по 250
  int hist[B + 1] = {0};
  int last = -1;
  for (int i = 0; i < N; i++) {
    if (!lvl[i]) continue;
    if (last >= 0) {
      uint32_t d = ts[i] - ts[last];
      int b = d / 250;
      hist[b > B ? B : b]++;
    }
    last = i;
  }
  pos = 0;
  for (int b = 0; b <= B; b++) {
    if (!hist[b]) continue;
    if (b < B)
      pos += snprintf(line + pos, sizeof(line) - pos, "%d-%d:%d ", b * 250, b * 250 + 249, hist[b]);
    else
      pos += snprintf(line + pos, sizeof(line) - pos, ">=%d:%d ", B * 250, hist[b]);
    if (pos > 150) {
      ESP_LOGI(TAG, "гіст.: %s", line);
      pos = 0;
      line[0] = 0;
    }
  }
  if (pos) ESP_LOGI(TAG, "гіст.: %s", line);
}

}  // namespace taho_diag
