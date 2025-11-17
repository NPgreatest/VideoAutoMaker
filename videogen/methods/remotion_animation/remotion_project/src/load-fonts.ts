import { loadFont } from "@remotion/google-fonts/Inter";

const { fontFamily } = loadFont('normal', {
  weights: ["400", "600", "900"],
  subsets: ["latin"],
  /**
   * 减少请求次数，确保渲染更稳定。
   * 只加载当前动画中实际使用的字重。
   */
});

export { fontFamily };
