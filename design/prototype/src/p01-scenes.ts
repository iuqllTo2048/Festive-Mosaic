// Coordinates refer to the supplied 1586 × 992 default image, never the expanded art.
export type SceneKey = 'spring' | 'qingming' | 'duanwu' | 'qixi' | 'mid-autumn'
export interface FestivalScene {
  key: SceneKey
  festivalId: string
  name: string
  file: string
  path: string
  origin: [number, number]
}
export const ART_BOUNDS = { x: 0, y: 85, width: 1586, height: 907 }
export const scenes: FestivalScene[] = [
  {key:'spring',festivalId:'chunjie',name:'春节',file:'02_hover_spring_festival_fullscreen.png',origin:[420,355],path:'M0 95 C190 70 180 205 340 218 C480 220 645 190 682 325 C695 410 740 448 793 505 C650 555 648 520 520 484 C330 426 294 565 0 478 Z'},
  {key:'qingming',festivalId:'qingming',name:'清明',file:'03_hover_qingming_fullscreen.png',origin:[310,715],path:'M0 478 C294 565 330 426 520 484 C648 520 650 555 793 505 C721 638 600 635 556 735 C490 855 475 945 325 992 H0 Z'},
  {key:'duanwu',festivalId:'duanwu',name:'端午',file:'04_hover_duanwu_fullscreen.png',origin:[840,795],path:'M793 505 C818 610 875 608 938 640 C1020 660 1060 790 1185 780 C1370 765 1480 720 1586 785 V992 H325 C475 945 490 855 556 735 C600 635 721 638 793 505 Z'},
  {key:'qixi',festivalId:'qixi',name:'七夕',file:'05_hover_qixi_fullscreen.png',origin:[1280,600],path:'M793 505 C858 500 900 518 900 518 C988 559 1063 547 1135 487 C1230 416 1440 350 1586 383 V785 C1480 720 1370 765 1185 780 C1060 790 1020 660 938 640 C875 608 818 610 793 505 Z'},
  {key:'mid-autumn',festivalId:'zhongqiu',name:'中秋',file:'06_hover_mid_autumn_fullscreen.png',origin:[1170,320],path:'M793 505 C740 448 695 410 765 302 C820 180 1055 225 1240 148 C1400 50 1470 80 1586 95 V383 C1440 350 1230 416 1135 487 C1063 547 988 559 900 518 C858 500 823 502 793 505 Z'},
]
export const sceneByKey = (key: SceneKey) => scenes.find(scene => scene.key === key)!
export const p01Asset = (path: string) => `${import.meta.env.BASE_URL}p01/${path}`
