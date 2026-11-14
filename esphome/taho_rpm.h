// Оберти з TAHO (вихід LM393 на GPIO14), стійкі до перешкод регулятора зарядки генератора.
//
// Що показала діагностика (14.11.2026): через ~7 с після пуску регулятор зарядки ламає сигнал,
// і на кожен період припадає 2-3 зайві фронти, тому простий лічильник показує 3800-4500 замість ~3050.
// Але половина періоду, де сигнал TAHO низький (вихід LM393 HIGH), лишається чистою (~1,45-1,75 мс)
// і закінчується справжнім фронтом. Тому:
//   1. Мітка = фронт вниз після HIGH довше за 1,3 мс. Між мітками — ціле число періодів.
//   2. Інтервал 2,6-4,2 мс = 1 період, 5,2-8,4 мс = 2 періоди (2380-3850 об/хв при 6 імп/оберт).
//   3. Раз на секунду оберти = медіана цих інтервалів.
//   4. Нижче ~2300 об/хв (прокрутка, зупинка) перешкод немає, там працює звичайний лічильник
//      фронтів з фільтром 1,8 мс.
// На записаних фронтах (обидва проводи котушки, з перемичкою на C3 і без) метод дав 3030-3170 об/хв
// у кожному записі, а лічильник показував до 4500.
#pragma once
#include <Arduino.h>
#include <algorithm>
#include "esp_timer.h"
#include "soc/gpio_struct.h"

namespace taho_rpm {

static const int PIN = 14;
static const int PULSES_PER_REV = 6;
static const uint32_t FILTER_US = 1800;      // фільтр лічильника фронтів
static const uint32_t MARK_HIGH_US = 1300;   // мінімальна чиста половина періоду
static const uint32_t P1_MIN = 2600, P1_MAX = 4200;
static const uint32_t P2_MIN = 5200, P2_MAX = 8400;
static const float MARKER_RPM_FROM = 2300;  // вище цього берем медіану інтервалів між мітками
static const int Q = 128;                    // буфер інтервалів (більше, ніж мітки за секунду)
static const uint32_t FAST_WINDOW_US = 200000;  // вікно швидких обертів для відпускання стартера
static const int F = 128;                    // буфер часу фронтів (3600 об/хв = 72 фронти за 0,2 с)

static volatile uint32_t filt_rising = 0;
static volatile uint32_t last_valid_us = 0;
static volatile uint32_t rise_us = 0;
static volatile bool high_seen = false;
static volatile uint32_t last_mark_us = 0;
static volatile uint32_t q[Q];
static volatile uint32_t q_head = 0;  // пише тільки переривання
static volatile uint32_t fts[F];      // час відфільтрованих фронтів вгору
static volatile uint32_t f_head = 0;

static void IRAM_ATTR isr() {
  uint32_t now = (uint32_t) esp_timer_get_time();
  uint8_t level = (GPIO.in >> PIN) & 1;
  if (level) {
    rise_us = now;
    high_seen = true;
    if ((uint32_t) (now - last_valid_us) >= FILTER_US) {
      last_valid_us = now;
      filt_rising++;
      fts[f_head % F] = now;
      f_head++;
    }
    return;
  }
  if (!high_seen) return;
  high_seen = false;
  if ((uint32_t) (now - rise_us) < MARK_HIGH_US) return;
  uint32_t d = now - last_mark_us;
  last_mark_us = now;
  uint32_t p = 0;
  if (d >= P1_MIN && d <= P1_MAX) p = d;
  else if (d >= P2_MIN && d <= P2_MAX) p = d / 2;
  if (p) {
    q[q_head % Q] = p;
    q_head++;
  }
}

static void setup() {
  pinMode(PIN, INPUT);
  attachInterrupt(digitalPinToInterrupt(PIN), isr, CHANGE);
}

// Швидкі оберти за останні 0,2 с (крок 50 об/хв) — щоб відпустити стартер одразу, як двигун завівся,
// а не чекати секундного виміру. Перешкоди на ходу тут не важливі: потрібен лише поріг ~1500.
static float fast_rpm() {
  uint32_t now = (uint32_t) esp_timer_get_time();
  uint32_t head = f_head;
  int n = 0;
  while (n < F && (uint32_t) n < head) {
    if ((uint32_t) (now - fts[(head - 1 - n) % F]) > FAST_WINDOW_US) break;
    n++;
  }
  return (float) n * 60e6f / PULSES_PER_REV / FAST_WINDOW_US;
}

// Викликати раз на секунду. Повертає оберти/хв; count_rpm — оберти за лічильником фронтів (для логу).
static float update(float *count_rpm) {
  static uint32_t prev_count = 0, q_tail = 0;
  static float last_good = 0;
  static int hold = 0;
  uint32_t c = filt_rising;
  float by_count = (float) (c - prev_count) * 60.0f / PULSES_PER_REV;
  prev_count = c;
  if (count_rpm) *count_rpm = by_count;

  uint32_t head = q_head;
  if (head - q_tail > (uint32_t) Q) q_tail = head - Q;
  uint32_t buf[Q];
  int n = 0;
  for (; q_tail != head; q_tail++) buf[n++] = q[q_tail % Q];

  if (by_count < MARKER_RPM_FROM) {
    hold = 0;
    last_good = 0;
    return by_count;
  }
  if (n >= 1) {
    std::nth_element(buf, buf + n / 2, buf + n);
    last_good = 60e6f / PULSES_PER_REV / (float) buf[n / 2];
    hold = 3;
    return last_good;
  }
  // двигун крутиться, але за цю секунду чистих міток не було: тримаємо останнє значення до 3 с
  if (hold > 0 && last_good > 0) {
    hold--;
    return last_good;
  }
  return by_count;
}

}  // namespace taho_rpm
