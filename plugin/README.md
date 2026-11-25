# PS5 Boot Installer — локальный плагин Roblox Studio

**Готовый файл:** [`PS5BootInstaller.rbxm`](PS5BootInstaller.rbxm)

Это локальный Studio-плагин, а не Marketplace asset. Он устанавливает всю логику PS5 Boot Experience в текущий place одним нажатием — Rojo для установки не нужен.

## Установка

1. Скачайте `PS5BootInstaller.rbxm` из этой папки.
2. В Roblox Studio откройте **Plugins → Manage Plugins** и выберите **Install Local Plugin / Install from File** (название может немного отличаться между версиями Studio).
3. Выберите `PS5BootInstaller.rbxm` и перезапустите Studio, если Studio попросит это сделать.
4. Откройте нужный place. В верхней панели появится вкладка **PS5 Boot**.
5. Нажмите кнопку **Install PS5 Boot Experience**.
6. Нажмите **Play**. Сервер создаст `Workspace.PS5Console`; подойдите к ней, наведите центр экрана и удерживайте **E**.

Если в вашей сборке Studio нет пункта установки из файла, поместите `.rbxm` в локальную папку `Plugins` Studio и перезапустите Studio. Не загружайте файл в Marketplace, если не хотите публиковать его как собственный плагин.

## Что создаёт кнопка

```text
ReplicatedStorage
└─ PS5BootShared
   └─ ConsoleConfig

ServerScriptService
└─ PS5BootExperience
   ├─ Bootstrap
   └─ Console
      ├─ ConsoleBuilder
      └─ ConsoleController

StarterPlayer
└─ StarterPlayerScripts
   └─ PS5BootExperience
      └─ ConsoleClient
```

Плагин обновляет только эти namespaced-объекты. Остальное содержимое place не удаляется. Перед и после установки создаются точки истории Studio, а после успеха выделяется `ServerScriptService.PS5BootExperience`.

## Важные настройки

После установки настройте `ReplicatedStorage.PS5BootShared.ConsoleConfig`:

- `SpawnCFrame` — положение и поворот консоли;
- `Interaction.HoldDuration` — длительность удерживания `E`;
- `Cinematic.BlackoutPersistenceSeconds = 0` — сохраняет финальную темноту;
- положительное значение `BlackoutPersistenceSeconds` возвращает игроку камеру и управление;
- `Audio.PowerOnSoundId` — только для звука, на который у вас есть права.

## Проверка файла

`PS5BootInstaller.rbxm` — настоящий binary Roblox model с одним `Script` в режиме `RunContext.Plugin`. Исходник установщика находится в `PS5BootInstaller.plugin.lua`; он генерируется из актуальных файлов `src/` скриптом [`../tools/build-plugin.cjs`](../tools/build-plugin.cjs).
