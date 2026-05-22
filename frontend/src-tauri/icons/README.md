# Icone applicazione SCO Compliance OS

Cartella placeholder per il set completo di icone richiesto dal bundler Tauri 2
per la generazione di installer multi-OS (MSI/NSIS Windows + DMG Mac + AppImage
/ deb / rpm Linux).

## Set richiesto

Quando il logo definitivo SCO sarà disponibile (PNG sorgente almeno 1024×1024,
sfondo trasparente, identità visiva approvata):

### Windows (.ico multi-res)

Un singolo file `icon.ico` con dentro 5 risoluzioni:

| Dimensione | Uso                                    |
|------------|----------------------------------------|
| 16×16      | Tray icon, file explorer ridotto       |
| 32×32      | Tray icon HiDPI, file explorer normale |
| 48×48      | Desktop shortcut                       |
| 64×64      | Sistema vario                          |
| 256×256    | Sistema HiDPI, properties dialog       |

Genera con ImageMagick:

```powershell
magick logo-sco-1024.png -define icon:auto-resize=16,32,48,64,256 icon.ico
```

### macOS (.icns)

Un singolo file `icon.icns` con dentro le risoluzioni richieste da Apple:

| Dimensione | Nome interno icns |
|------------|--------------------|
| 16×16      | icon_16x16         |
| 32×32      | icon_16x16@2x      |
| 32×32      | icon_32x32         |
| 64×64      | icon_32x32@2x      |
| 128×128    | icon_128x128       |
| 256×256    | icon_128x128@2x    |
| 256×256    | icon_256x256       |
| 512×512    | icon_256x256@2x    |
| 512×512    | icon_512x512       |
| 1024×1024  | icon_512x512@2x    |

Genera con `iconutil` su Mac, o con `png2icns` su Linux.

### Linux + Tauri bundler (PNG flat)

File PNG separati referenziati da `tauri.conf.json`:

- `32x32.png`
- `128x128.png`
- `128x128@2x.png` (256×256 effettivi)

Più una versione "icon" principale `icon.png` 512×512 per AppImage hicolor.

## Tool consigliato

[`tauri icon`](https://v2.tauri.app/reference/cli/#icon) genera tutto il set
da un singolo PNG sorgente con un solo comando:

```bash
cd frontend
pnpm tauri icon path/to/logo-sco-1024.png
```

Questo popola automaticamente `icons/` con tutte le varianti richieste,
incluso il `.ico` Windows multi-res e l'`.icns` macOS.

## Placeholder corrente

Al momento questa cartella è vuota. Il primo `pnpm tauri build` fallirà con
errore "icon not found" finché non viene popolata. Per testare lo scaffolding
prima del logo definitivo è possibile usare un'icona placeholder generata
con `tauri icon` da qualsiasi PNG square.
