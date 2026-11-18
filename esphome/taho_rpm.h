// Оберти з TAHO (вихід LM393 на GPIO14), стійкі до перешкод регулятора зарядки генератора.
//
// Сигнал береться з одного проводу котушки зарядки, яку навантажує реле (регулятор) зарядки. Коли акумулятор
// підзарядився (через 4-7 с після пуску), реле "рубає" сигнал і на кожен період припадає 2-4 зайві фронти:
// простий лічильник показує 3700-4500 замість ~3000.
//
// Що спільне в усіх записах (14.11.2026 — старе реле, 18.11.2026 — нове реле після КЗ): раз на період
// (або раз на половину періоду, поки реле не рубає) є ТИХА ДІЛЯНКА — 1,3-1,8 мс без жодного фронту.
// Перешкоди реле йдуть пачками з паузами до ~0,75 мс. Тому:
//   1. Мітка = будь-який фронт після тиші довше за 1,3 мс (рівень сигналу не важливий: частину коротких
//      фронтів переривання може пропустити, і рівень тоді читається не той).
//   2. Інтервал між мітками 2,6-4,2 мс = 1 період, 5,2-8,4 мс = 2 періоди, 1,3-2,1 мс = пів періоду
//      (чистий сигнал, дві тихі половини). Інше — відкидаємо.
//   3. Раз на секунду оберти = медіана цих інтервалів.
//   4. Нижче ~2300 об/хв (прокрутка, зупинка) перешкод немає, там працює звичайний лічильник
//      фронтів вгору з фільтром 1,8 мс.
// На записі 18.11 (41 запис по 600 фронтів, чистий сигнал і з реле, з навантаженням і без) метод дав
// 2955-3160 об/хв у кожному записі, а лічильник показував 3700-4000. Попередній метод (чиста половина
// HIGH > 1,3 мс) з новим реле міток не знаходив.
#pragma once
#include <Arduino.h>
#include <algorithm>
#include "esp_timer.h"
#include "soc/gpio_struct.h"

namespace taho_rpm {

static const int PIN = 14;
static const int PULSES_PER_REV = 6;
static const uint32_t FILTER_US = 1800;      // фільтр лічильника фронтів
static const uint32_t QUIET_US = 1300;       // тиша перед фронтом, після якої фронт = мітка
static const uint32_t P1_MIN = 2600, P1_MAX = 4200;  // 1 період
static const uint32_t P2_MIN = 5200, P2_MAX = 8400;  // 2 періоди (одну мітку пропустили)
static const uint32_t H_MIN = 1300, H_MAX = 2100;    // пів періоду (чистий сигнал)
static const float MARKER_RPM_FROM = 2300;  // вище цього берем медіану інтервалів між мітками
static const int Q = 128;                    // буфер інтервалів (більше, ніж мітки за секунду)
static const uint32_t FAST_WINDOW_US = 200000;  // вікно швидких обертів для відпускання стартера
static const int F = 128;                    // буфер часу фронтів (3600 об/хв = 72 фронти за 0,2 с)

static volatile uint32_t filt_rising = 0;
static volatile uint32_t last_valid_us = 0;
static volatile uint32_t last_edge_us = 0;
static volatile uint32_t last_mark_us = 0;
static volatile uint32_t q[Q];
static volatile uint32_t q_head = 0;  // пише тільки переривання
static volatile uint32_t fts[F];      // час відфільтрованих фронтів вгору
static volatile uint32_t f_head = 0;

static void IRAM_ATTR isr() {
  uint32_t now = (uint32_t) esp_timer_get_time();
  uint8_t level = (GPIO.in >> PIN) & 1;
  if (level && (uint32_t) (now - last_valid_us) >= FILTER_US) {
    last_valid_us = now;
    filt_rising++;
    fts[f_head % F] = now;
    f_head++;
  }
  uint32_t quiet = now - last_edge_us;
  last_edge_us = now;
  if (quiet < QUIET_US) return;
  uint32_t d = now - last_mark_us;
  last_mark_us = now;
  uint32_t p = 0;
  if (d >= P1_MIN && d <= P1_MAX) p = d;
  else if (d >= P2_MIN && d <= P2_MAX) p = d / 2;
  else if (d >= H_MIN && d <= H_MAX) p = d * 2;
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
