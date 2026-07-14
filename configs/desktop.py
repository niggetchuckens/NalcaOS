kde_plasma = ["plasma", "sddm", "konsole", "dolphin"]
gnome = ["gnome", "gdm"]
xfce = ["xfce4", "xfce4-goodies", "lightdm", "lightdm-gtk-greeter"]
cinnamon = ["cinnamon", "nemo", "lightdm", "lightdm-gtk-greeter"]
mate = ["mate", "mate-extra", "lightdm", "lightdm-gtk-greeter"]
lxqt = ["lxqt", "sddm"]
lxde = ["lxde", "lxdm"]
budgie = ["budgie-desktop", "lightdm", "lightdm-gtk-greeter"]
deepin = ["deepin", "deepin-extra", "lightdm", "lightdm-gtk-greeter"]
pantheon = ["pantheon", "lightdm", "pantheon-lightdm-greeter"]
enlightenment = ["enlightenment", "terminology", "lightdm", "lightdm-gtk-greeter"]
trinity = ["tde-meta", "tdm"]
cosmic = ["cosmic-session", "cosmic-greeter"]

hyprland = ["hyprland", "kitty", "waybar", "sddm", "wofi"]
sway = ["sway", "swaybg", "swaylock", "swayidle", "waybar", "sddm", "alacritty", "dmenu"]
river = ["river", "foot", "waybar", "swaybg", "wofi"]
wayfire = ["wayfire", "wayfire-plugins-extra", "alacritty", "wofi", "waybar"]
labwc = ["labwc", "foot", "waybar", "swaybg", "wofi"]
niri = ["niri", "waybar", "alacritty", "fuzzel"]
cage = ["cage", "alacritty"]
hikari = ["hikari", "alacritty", "waybar"]

i3 = ["i3-wm", "i3status", "i3lock", "dmenu", "alacritty", "lightdm", "lightdm-gtk-greeter"]
bspwm = ["bspwm", "sxhkd", "polybar", "rofi", "alacritty", "lightdm", "lightdm-gtk-greeter"]
awesome = ["awesome", "rofi", "alacritty", "lightdm", "lightdm-gtk-greeter"]
xmonad = ["xmonad", "xmonad-contrib", "xmobar", "rofi", "alacritty", "lightdm", "lightdm-gtk-greeter"]
qtile = ["qtile", "rofi", "alacritty", "lightdm", "lightdm-gtk-greeter"]
dwm = ["dwm", "dmenu", "st", "lightdm", "lightdm-gtk-greeter"]
openbox = ["openbox", "obconf", "tint2", "rofi", "alacritty", "lightdm", "lightdm-gtk-greeter"]
icewm = ["icewm", "rofi", "alacritty", "lightdm", "lightdm-gtk-greeter"]
fluxbox = ["fluxbox", "rofi", "alacritty", "lightdm", "lightdm-gtk-greeter"]
herbstluftwm = ["herbstluftwm", "dmenu", "alacritty", "lightdm", "lightdm-gtk-greeter"]
spectrwm = ["spectrwm", "dmenu", "alacritty", "lightdm", "lightdm-gtk-greeter"]
jwm = ["jwm", "rofi", "alacritty", "lightdm", "lightdm-gtk-greeter"]
dk = ["dk", "sxhkd", "polybar", "rofi", "alacritty", "lightdm", "lightdm-gtk-greeter"]
stumpwm = ["stumpwm", "rofi", "alacritty", "lightdm", "lightdm-gtk-greeter"]

desktops = {
    "1": ("KDE Plasma", kde_plasma, "sddm"),
    "2": ("GNOME", gnome, "gdm"),
    "3": ("XFCE", xfce, "lightdm"),
    "4": ("Cinnamon", cinnamon, "lightdm"),
    "5": ("MATE", mate, "lightdm"),
    "6": ("LXQt", lxqt, "sddm"),
    "7": ("LXDE", lxde, "lxdm"),
    "8": ("Budgie", budgie, "lightdm"),
    "9": ("Deepin", deepin, "lightdm"),
    "10": ("Hyprland", hyprland, "sddm"),
    "11": ("Sway", sway, "sddm"),
    "12": ("i3-wm", i3, "lightdm"),
    "13": ("bspwm", bspwm, "lightdm"),
    "14": ("Awesome", awesome, "lightdm"),
    "15": ("xmonad", xmonad, "lightdm"),
    "16": ("qtile", qtile, "lightdm"),
    "17": ("dwm", dwm, "lightdm"),
    "18": ("None (TTY only)", None, None)
}

def de_select():
    de = None
    options = list(desktops.keys())
    
    while de not in options:
        print("\nSelect your Desktop Environment or Window Manager:")
        for key, value in desktops.items():
            print(f"{key}) {value[0]}")
        de = input(f"Selection (1-{len(options)}): ").strip()
    
    selected_de = desktops[de]
    if selected_de[1] is None:
        return None, None
    
    return " ".join(selected_de[1]), selected_de[2]
