# Brain in a Vat: Imports Catalogue

The full Win32 API surface used by `Vat_1.9.exe`, grouped by purpose. 186 unique imports across 6 system DLLs. **No** WinSock, MFC*.dll, OLE/COM, RPC, or zlib DLL - those subsystems either aren't used (no networking) or are statically linked into the binary (MFC and zlib are baked in).

This is the entire engine-host surface area. The Vat is a self-contained .exe that talks to:
- The user (via the GUI subsystems)
- The Creatures Engine (via the Win32 IPC subsystem - kernel objects + shared memory)
- The local filesystem (CreaturesArchive files, log files, the `*.catalogue` files)
- The Windows registry (to find the running game's IPC name prefix)

## DLL summary

| DLL | Imports | Purpose |
|---|---|---|
| KERNEL32.DLL | 90 | Process, file, memory, IPC primitives, locale |
| USER32.DLL | 65 | Windows, messages, menus, dialogs |
| GDI32.DLL | 24 | Drawing primitives (the brain viewport) |
| COMCTL32.DLL | 3 | Toolbar + status bar |
| ADVAPI32.DLL | 3 | Registry access only |
| COMDLG32.DLL | 1 | File-open dialog |

## KERNEL32: IPC primitives (the engine connection)

This subset is the entire shared-memory IPC surface. Every imported call here is used either by the connect handshake (see [03-ipc-protocol.md](03-ipc-protocol.md)) or by the per-tick communication.

| Function | Role in IPC |
|---|---|
| `OpenMutexA` | Open the engine's named mutex `<name>_mutex` |
| `OpenEventA` | Open `<name>_request` and `<name>_result` event handles |
| `OpenFileMappingA` | Open the shared memory section `<name>_mem` |
| `MapViewOfFile` | Map the shared memory into the Vat process |
| `UnmapViewOfFile` | Unmap on disconnect |
| `SetEvent` | Signal `_request` (Vat → engine) |
| `ResetEvent` | Reset events between transactions |
| `WaitForSingleObject` | Wait for `_result` |
| `WaitForMultipleObjects` | Wait for `_result` plus possibly a quit signal |
| `ReleaseMutex` | Release the IPC mutex after a transaction |
| `GetHandleInformation` | Probably a sanity check after `OpenMutexA` |
| `CloseHandle` | Close all four handles on shutdown |
| `OpenProcess` | Open the engine process (uncertain purpose - possibly for `WaitForSingleObject` to detect engine death) |

## KERNEL32: file I/O (CreaturesArchive, logs, catalogue files)

| Function | Role |
|---|---|
| `CreateFileA`, `OpenFile`, `_lclose` | File open/close (mixed legacy and modern API) |
| `ReadFile`, `WriteFile` | Stream I/O for CreaturesArchive serialisation |
| `SetFilePointer`, `SetEndOfFile`, `FlushFileBuffers` | Seek, truncate, sync |
| `GetFileAttributesA`, `GetFileSize`, `GetFileType` | File metadata |
| `GetFullPathNameA`, `GetCurrentDirectoryA`, `SetCurrentDirectoryA` | Path resolution |
| `FindFirstFileA`, `FindNextFileA`, `FindClose` | Directory iteration (catalogue lookup) |
| `MoveFileA`, `DeleteFileA` | File mutation |

## KERNEL32: process / runtime

| Function | Role |
|---|---|
| `GetCommandLineA`, `GetStartupInfoA`, `GetEnvironmentStrings*`, `FreeEnvironmentStringsA` | Standard CRT startup |
| `GetCurrentProcess`, `TerminateProcess`, `ExitProcess`, `GetVersion`, `GetVersionExA` | Process control |
| `GetModuleFileNameA`, `GetModuleHandleA`, `LoadLibraryA`, `GetProcAddress` | DLL/module access (MSVCRT-typical) |
| `GetStdHandle`, `SetStdHandle`, `SetHandleCount`, `SetConsoleCtrlHandler` | Standard I/O setup |
| `RaiseException`, `RtlUnwind`, `SetUnhandledExceptionFilter`, `UnhandledExceptionFilter` | C++ EH / SEH machinery |
| `IsBadCodePtr`, `IsBadReadPtr`, `IsBadWritePtr` | Defensive pointer checks |
| `GetLastError`, `FormatMessageA` | Error handling |

## KERNEL32: memory

| Function | Role |
|---|---|
| `HeapCreate`, `HeapDestroy`, `HeapAlloc`, `HeapFree`, `HeapReAlloc`, `HeapSize` | Custom heaps (CRT) |
| `VirtualAlloc`, `VirtualFree` | Page-level allocation (CRT large allocs) |

## KERNEL32: locale (CRT internal - not interesting)

`CompareStringA/W`, `LCMapStringA/W`, `MultiByteToWideChar`, `WideCharToMultiByte`, `EnumSystemLocalesA`, `GetACP`, `GetOEMCP`, `GetCPInfo`, `IsValidCodePage`, `IsValidLocale`, `GetLocaleInfoA/W`, `GetStringTypeA/W`, `GetUserDefaultLCID`, `GetTimeZoneInformation`, `FileTimeToSystemTime`, `FileTimeToLocalFileTime`, `SetEnvironmentVariableA`. All STL/locale machinery, ignore.

## USER32: window management

`RegisterClassExA`, `CreateWindowExA`, `DestroyWindow`, `ShowWindow`, `MoveWindow`, `BringWindowToTop`, `SetActiveWindow`, `IsWindow`, `IsChild`, `GetWindow`, `GetParent`, `GetDesktopWindow`, `GetWindowLongA`, `GetWindowRect`, `GetClientRect`, `GetSystemMetrics`, `GetSysColor`, `GetSysColorBrush`.

## USER32: messages and input

`GetMessageA`, `PeekMessageA`, `DispatchMessageA`, `TranslateMessage`, `SendMessageA`, `PostQuitMessage`, `DefWindowProcA`, `IsDialogMessageA`, `LoadCursorA`, `SetCursor`, `LoadIconA`, `LoadStringA`, `KillTimer`, `SetTimer`, `GetCursorPos`, `PtInRect`, `ClientToScreen`, `ScreenToClient`.

## USER32: drawing / paint cycle

`BeginPaint`, `EndPaint`, `GetDC`, `ReleaseDC`, `InvalidateRect`, `RedrawWindow`, `UpdateWindow`, `SetWindowTextA`, `DrawTextA`. The paint cycle for the BrainViewport hangs off these (combined with GDI primitives below).

## USER32: dialog / menu

`CreateDialogParamA`, `GetDlgItem`, `MessageBoxA`, `CreateMenu`, `CreatePopupMenu`, `LoadMenuA`, `SetMenu`, `IsMenu`, `GetSubMenu`, `GetMenuItemCount`, `AppendMenuA`, `InsertMenuA`, `RemoveMenu`, `DeleteMenu`, `EnableMenuItem`, `CheckMenuItem`, `TrackPopupMenu`. The right-click context menus on neurons/dendrites mentioned in the readme are built with `TrackPopupMenu`.

## USER32: scroll bars

`GetScrollInfo`, `SetScrollInfo`. The brain viewport supports scrolling.

## GDI32: drawing primitives (the brain viewport's painting toolkit)

| Function | Role |
|---|---|
| `CreateCompatibleDC`, `CreateCompatibleBitmap`, `BitBlt`, `DeleteDC`, `DeleteObject` | Off-screen buffer for flicker-free brain rendering |
| `CreateBrushIndirect`, `CreateSolidBrush`, `GetStockObject`, `SelectObject` | Brushes for filling lobe rectangles, neuron dots |
| `CreatePen`, `MoveToEx`, `LineTo`, `Polyline` | Lines for tracts and dendrites |
| `Rectangle`, `Ellipse` *(no `Ellipse`)*, `FillRect` *(via brush)* | Rectangles for lobes; neurons probably as small filled rectangles |
| `CreateFontIndirectA`, `TextOutA`, `GetTextExtentPointA`, `SetTextColor`, `SetBkColor`, `SetBkMode` | Text labels for lobes / neurons / dendrites |
| `SetViewportExtEx`, `SetViewportOrgEx`, `SetWindowExtEx`, `SetWindowOrgEx` | Logical-to-device coordinate mapping (zoom/pan) |

`Ellipse` is *not* imported - neurons are drawn as rectangles, not circles. Useful detail when reimplementing.

## ADVAPI32: registry (small surface)

`RegOpenKeyA`, `RegQueryValueExA`, `RegCloseKey`. Read-only. Used to look up the engine name prefix from `HKEY_CURRENT_USER\Software\CyberLife Technology\Creatures Engine`. No writes.

## COMCTL32: toolbar + status

`InitCommonControls`, `CreateToolbarEx`, `CreateStatusWindowA`. The toolbar (with the readme's "IN" instinct-processing button, loop button, play button) is a single `CreateToolbarEx` call. Status bar at the bottom.

## COMDLG32: file open

`GetOpenFileNameA` only - the offline-mode "open genome" dialog.

## What this tells us about the system architecture

1. **No networking.** No WinSock = no TCP/IP, no HTTP. Engine connectivity is 100% via local kernel objects.
2. **No COM/OLE.** Pure Win32. No DCOM, no out-of-proc objects.
3. **Self-contained.** Beyond the 6 system DLLs everything is statically linked.
4. **Small attack/dependency surface.** This is good for porting, lifting, or reimplementing - there's no opaque external dependency to worry about.
5. **GUI is plain MFC + GDI.** The brain rendering is just rectangles, lines, and text. Reimplementable in any modern toolkit (web canvas, Qt, Skia) in a small fraction of the original development effort.
6. **Drawing is non-trivial but well-bounded.** ~24 GDI calls cover the entire visualisation. We can map each call to an SVG primitive or canvas operation 1:1.
