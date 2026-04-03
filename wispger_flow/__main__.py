"""WispGer Flow — Voice to text, refined."""

def main():
    from wispger_flow.constants import HOTKEY
    from wispger_flow.ui.app import WispGerFlow
    print(f"\n  WispGer Flow\n  {HOTKEY} to record. Release to paste.\n")
    WispGerFlow().mainloop()

if __name__ == "__main__":
    main()
