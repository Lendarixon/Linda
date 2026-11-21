"""Repaint the WebView2 host after minimize/restore without reloading the page.

WinForms WebView2 can retain a blank composition surface after a native restore.
Keep the document and draft alive; resynchronize visibility and bounds on the UI
thread once per restore. No polling, GPU flags, cache deletion or navigation.
"""
import logging
import sys

log = logging.getLogger(__name__)

class RestoreState:
    def __init__(self):
        self.minimized = False
        self.pending = False

    def changed(self, minimized):
        if minimized:
            self.minimized = True
            self.pending = False
            return False
        if self.minimized:
            self.minimized = False
            self.pending = True
            return True
        return False

    def take(self, minimized, closed):
        if closed or minimized or not self.pending:
            return False
        self.pending = False
        return True

def install(window):
    """Attach only to this application's Windows host after it has been shown."""
    def shown():
        host = window.native
        if host is None or not hasattr(host, 'webview'):
            return
        try:
            if not log.handlers:
                log.addHandler(logging.StreamHandler(sys.stderr))
                log.setLevel(logging.INFO)
                log.propagate = False
            from System import Action
            from System.Drawing import Rectangle
            from System.Windows.Forms import FormWindowState, Timer

            def attach():
                if host.IsDisposed or hasattr(host, '_linda_restore_recovery'):
                    return
                state = RestoreState()
                timer = Timer()
                timer.Interval = 120
                control = host.webview

                def minimized():
                    return host.WindowState == FormWindowState.Minimized

                def repaint(sender=None, args=None):
                    timer.Stop()
                    if not state.take(minimized(), host.IsDisposed or control.IsDisposed):
                        return
                    try:
                        # A one-pixel bounds change forces WebView2's composition
                        # controller to recreate its visible surface. No reload.
                        bounds = host.ClientRectangle
                        if bounds.Width < 2 or bounds.Height < 2:
                            return
                        control.Visible = False
                        control.Bounds = Rectangle(bounds.X,bounds.Y,bounds.Width-1,bounds.Height)
                        control.Visible = True
                        control.Bounds = bounds
                        host.PerformLayout()
                        control.Invalidate(True)
                        control.Update()
                        log.info('WebView2 restore repaint completed')
                    except Exception:
                        log.exception('WebView2 restore repaint failed')

                def changed(sender=None, args=None):
                    if host.IsDisposed:
                        return
                    if state.changed(minimized()):
                        timer.Stop()
                        timer.Start()

                def closed(sender=None, args=None):
                    timer.Stop()
                    timer.Dispose()

                timer.Tick += repaint
                host.Resize += changed
                host.Activated += changed
                host.FormClosed += closed
                # Keep Python delegates alive for the lifetime of the host.
                host._linda_restore_recovery = (state,timer,repaint,changed,closed)
                def dock_downloads(sender=None, args=None):
                    try:  # the built-in download flyout (top-right by default) covered the Back / export buttons
                        core = control.CoreWebView2
                        if core is not None:
                            core.DefaultDownloadDialogCornerAlignment = type(core.DefaultDownloadDialogCornerAlignment)(2)  # BottomLeft
                    except Exception:
                        log.exception('WebView2 download flyout alignment failed')

                dock_downloads()
                control.CoreWebView2InitializationCompleted += dock_downloads
                host._linda_dock_downloads = dock_downloads
                log.info('WebView2 restore recovery attached')

            host.BeginInvoke(Action(attach))
        except Exception:
            log.exception('WebView2 restore recovery unavailable')

    window.events.shown += shown
