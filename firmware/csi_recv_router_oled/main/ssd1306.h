/*
 * SPDX-FileCopyrightText: 2026 Espressif Systems (Shanghai) CO LTD
 *
 * SPDX-License-Identifier: Apache-2.0
 */
/* Minimal self-contained SSD1306 128x64 I2C driver (esp_driver_i2c, IDF 5.x).

   This example code is in the Public Domain (or CC0 licensed, at your option.)

   Unless required by applicable law or agreed to in writing, this
   software is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
   CONDITIONS OF ANY KIND, either express or implied. */
#pragma once

#include <stdbool.h>
#include "esp_err.h"

#if CONFIG_OLED_ENABLE

#define SSD1306_W 128
#define SSD1306_H 64

/* Initialise I2C master bus + device and bring the panel up.
 * Uses CONFIG_OLED_SDA / CONFIG_OLED_SCL / CONFIG_OLED_I2C_ADDR. */
esp_err_t ssd1306_init(void);

/* Clear the local framebuffer (call ssd1306_display() to push it). */
void ssd1306_clear(void);

/* Draw a string with the built-in 5x7 font at pixel position x,
 * y must be a multiple of 8 (text row = y / 8). */
void ssd1306_draw_string(int x, int y, const char *str);

/* Normal (false) / inverted (true) video mode. */
void ssd1306_invert(bool invert);

/* Flush the full 1 KB framebuffer over I2C (page addressing mode). */
esp_err_t ssd1306_display(void);

#endif /* CONFIG_OLED_ENABLE */
