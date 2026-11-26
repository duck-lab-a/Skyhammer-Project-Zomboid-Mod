package skyhammer.aircraft;

/**
 * Pure, saved-combat-clock pose of the F-22 flight (Skyhammer_F22.lua's S.F22): ten jets in trail,
 * 0.4 s apart, straight and level along the strike's line at SPEED tiles a second, the lead over
 * the line's start at OVER seconds. Tile XY is the same as Skyhammer_Shadow.lua's raptorPose, so
 * each jet stays over its own shadow.
 */
public final class Raptor {
    /** The lead over the line's start; tiles a second; drawn from FROM until END (seconds). */
    public static final double OVER = 6.0, SPEED = 340, FROM = 3.5, END = 13.0;   // (Mach 1 at a tile a metre)
    /** Tiles behind the lead (0.4 s, 0.4 SPEED tiles, each), to its right, and up (S.F22.jets). */
    public static final double[][] JETS = {
        {0, -10, 0}, {136, 10, 2}, {272, -10, 4}, {408, 10, 0}, {544, -10, 2},
        {680, 10, 4}, {816, -10, 0}, {952, 10, 2}, {1088, -10, 4}, {1224, 10, 0},
    };
    public record Pose(boolean visible, double x, double y, double height, double yaw) {}
    private static final Pose HIDDEN = new Pose(false, 0, 0, 0, 0);
    private Raptor() {}

    /**
     * Jet (0..9) e seconds after the mark; (x, y) the line's start, floor its storey, heading the
     * flight's direction in tile space (radians), altitude its height above the floor (clamped 30..150).
     */
    public static Pose pose(int jet, double e, double x, double y, double floor, double heading, double altitude) {
        if (jet < 0 || jet >= JETS.length || !Double.isFinite(e + x + y + floor + heading + altitude)
                || e < FROM || e >= END) return HIDDEN;
        double[] j = JETS[jet];
        double c = Math.cos(heading), s = Math.sin(heading);
        double along = (e - OVER) * SPEED - j[0];
        return new Pose(true, x + c * along - s * j[1], y + s * along + c * j[1],
                floor * Projection.STOREY + Math.max(30, Math.min(150, altitude)) + j[2],
                Math.atan2(-c, -s));
    }
}
