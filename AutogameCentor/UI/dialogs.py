import tkinter as tk
from tkinter import messagebox

def ask_shadow_shop():
    root = tk.Tk()
    root.withdraw()
    return messagebox.askyesno(
        "상점 이용",
        "물약 / 주문서 구매를 할까요?\n\n아니요 → 상점 스킵"
    )
