// Preset PrimeVue dựa trên Aura, nhuộm màu primary theo brand EduFi.
// Đổi brand: sửa `teal`/`tealHover` trong `./colors.json`, không cần đụng file này.
import { definePreset } from "@primeuix/themes";
import Aura from "@primeuix/themes/aura";

import colors from "./colors.json";

const { teal, tealHover } = colors.brand;

// PrimeVue cần đủ 11 sắc độ (50-950) cho mỗi màu semantic. 500/600 lấy đúng
// hex brand (base/hover); các sắc độ còn lại nội suy bằng color-mix() để
// không phải tự bịa ra một bảng màu không có trong bộ nhận diện.
const tint = (pct) => `color-mix(in srgb, white ${pct}%, ${teal})`;
const shade = (pct) => `color-mix(in srgb, black ${pct}%, ${tealHover})`;

export default definePreset(Aura, {
  semantic: {
    primary: {
      50: tint(95),
      100: tint(90),
      200: tint(75),
      300: tint(55),
      400: tint(30),
      500: teal,
      600: tealHover,
      700: shade(15),
      800: shade(30),
      900: shade(45),
      950: shade(60),
    },
  },
});
