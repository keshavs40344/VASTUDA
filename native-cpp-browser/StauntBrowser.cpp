/**
 * Staunt Browser Ultra - Native C++ Engine Launcher
 * High-performance Windows native launcher written in standard modern C++ / Win32.
 * 
 * Features:
 * - Zero runtime dependencies (Pure Win32 API)
 * - Automatic Chromium hardware acceleration flags
 * - Isolated persistent profile directory
 * - Direct local network gigabit rendering
 */

#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <shellapi.h>
#include <shlobj.h>
#include <string>
#include <vector>

const wchar_t* APP_URL = L"https://web-production-2ac2a.up.railway.app/tools/staunt-browser?mode=direct";
const wchar_t* APP_NAME = L"Staunt Browser Ultra";

std::wstring GetLocalAppDataPath() {
    wchar_t path[MAX_PATH];
    if (SUCCEEDED(SHGetFolderPathW(NULL, CSIDL_LOCAL_APPDATA, NULL, 0, path))) {
        return std::wstring(path);
    }
    return L"C:\\Temp";
}

bool FileExists(const std::wstring& path) {
    DWORD dwAttrib = GetFileAttributesW(path.c_str());
    return (dwAttrib != INVALID_FILE_ATTRIBUTES && !(dwAttrib & FILE_ATTRIBUTE_DIRECTORY));
}

int WINAPI wWinMain(HINSTANCE hInstance, HINSTANCE hPrevInstance, PWSTR pCmdLine, int nCmdShow) {
    (void)hInstance;
    (void)hPrevInstance;
    (void)pCmdLine;
    (void)nCmdShow;

    // 1. Prepare isolated user data profile directory
    std::wstring localAppData = GetLocalAppDataPath();
    std::wstring profileDir = localAppData + L"\\StauntBrowserProfile";
    CreateDirectoryW(profileDir.c_str(), NULL);

    // 2. Candidate native Chromium engine paths
    std::vector<std::wstring> enginePaths;
    
    // Program Files (x86)
    wchar_t pfX86[MAX_PATH];
    if (SUCCEEDED(SHGetFolderPathW(NULL, CSIDL_PROGRAM_FILESX86, NULL, 0, pfX86))) {
        enginePaths.push_back(std::wstring(pfX86) + L"\\Microsoft\\Edge\\Application\\msedge.exe");
        enginePaths.push_back(std::wstring(pfX86) + L"\\Google\\Chrome\\Application\\chrome.exe");
    }

    // Program Files (64-bit)
    wchar_t pf64[MAX_PATH];
    if (SUCCEEDED(SHGetFolderPathW(NULL, CSIDL_PROGRAM_FILES, NULL, 0, pf64))) {
        enginePaths.push_back(std::wstring(pf64) + L"\\Microsoft\\Edge\\Application\\msedge.exe");
        enginePaths.push_back(std::wstring(pf64) + L"\\Google\\Chrome\\Application\\chrome.exe");
    }

    // 3. Command line flags for maximum GPU rasterization & direct rendering
    std::wstring args = L"--app=\"" + std::wstring(APP_URL) + L"\" "
                        L"--user-data-dir=\"" + profileDir + L"\" "
                        L"--disable-web-security "
                        L"--disable-site-isolation-trials "
                        L"--enable-gpu-rasterization "
                        L"--ignore-gpu-blocklist "
                        L"--enable-zero-copy "
                        L"--start-maximized";

    // 4. Launch native engine
    for (const auto& path : enginePaths) {
        if (FileExists(path)) {
            SHELLEXECUTEINFOW sei = { sizeof(sei) };
            sei.fMask = SEE_MASK_DEFAULT;
            sei.lpVerb = L"open";
            sei.lpFile = path.c_str();
            sei.lpParameters = args.c_str();
            sei.nShow = SW_MAXIMIZE;

            if (ShellExecuteExW(&sei)) {
                return 0; // Launched successfully
            }
        }
    }

    // Fallback: Default system browser
    ShellExecuteW(NULL, L"open", APP_URL, NULL, NULL, SW_SHOWNORMAL);
    return 0;
}
