package skyhammer.aircraft;

import java.lang.reflect.Field;
import java.lang.reflect.Method;
import zombie.characters.IsoGameCharacter;
import zombie.characters.IsoPlayer;

/**
 * The gunner seat's switch between Viewpoint's 3D view and its isometric one, done with Viewpoint's
 * own switch instead of its view cycle. The cycle (isometric -> first -> third) passes through third
 * person, and third person is a saved choice in Viewpoint (camera.thirdPersonOnFoot): a seat entered
 * from first person then came back in third person, and the next step of the cycle was the isometric
 * view again (log 2026-11-04 20:16).
 * Viewpoint 0.1.7: viewpoint.ViewSwitch.toggle(character, to3D), with its camera move; it drops a switch
 * asked while one is under way, so Lua asks again a moment later.
 * Viewpoint 0.1.6: viewpoint.FP.switchView(character, to3D), at once.
 * Everything is found by name: not part of the Viewpoint members Main checks for the renderer, and a
 * Viewpoint without either just leaves the seat on the cycle.
 */
final class ViewSwitchBridge {
    private static boolean looked;
    private static Field enabled;
    private static Method toggle;
    private static Method switchView;
    private static boolean reported;

    private ViewSwitchBridge() {}

    private static synchronized void look() {
        if (looked) return;
        looked = true;
        try {
            ClassLoader vp = viewpoint.render.FrameContext.class.getClassLoader();
            enabled = Class.forName("viewpoint.core.View", false, vp).getField("enabled");
            try {
                toggle = Class.forName("viewpoint.ViewSwitch", false, vp)
                        .getDeclaredMethod("toggle", IsoGameCharacter.class, boolean.class);
                toggle.setAccessible(true);
            } catch (ReflectiveOperationException e) {
                toggle = null;
                switchView = Class.forName("viewpoint.FP", false, vp)
                        .getDeclaredMethod("switchView", IsoGameCharacter.class, boolean.class);
                switchView.setAccessible(true);
            }
            System.out.println("[Skyhammer] gunner seat: Viewpoint view switch " + (toggle != null ? "ViewSwitch.toggle" : "FP.switchView"));
        } catch (Throwable t) {
            enabled = null; toggle = null; switchView = null;
            System.out.println("[Skyhammer] gunner seat: no direct Viewpoint view switch (" + t + "), its view cycle is used");
        }
    }

    static boolean known() {
        look();
        return enabled != null && (toggle != null || switchView != null);
    }

    static boolean on3D() {
        if (!known()) return false;
        try { return enabled.getBoolean(null); } catch (Throwable t) { return false; }
    }

    /** Asks for the 3D view (true) or the isometric one (false); false = not asked. */
    static boolean set(boolean want3D) {
        if (!known()) return false;
        IsoPlayer p = IsoPlayer.getInstance();
        if (p == null) return false;
        try {
            if (enabled.getBoolean(null) == want3D) return true;
            if (toggle != null) toggle.invoke(null, p, want3D);
            else switchView.invoke(null, p, want3D);
            return true;
        } catch (Throwable t) {
            if (!reported) { reported = true; System.out.println("[Skyhammer] gunner seat: Viewpoint view switch failed, its view cycle is used from now on: " + t); }
            enabled = null;     // known() false: Lua goes back to the view cycle
            return false;
        }
    }
}
