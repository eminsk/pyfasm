def main() -> int:
    print_str("======================================================================\n")
    print_str("     PyFASM Native x64 Mandelbrot Fractal (Fixed-Point Real-Time)     \n")
    print_str("======================================================================\n")

    t0 = get_tick_count()

    # ASCII display dimensions
    width = 72
    height = 28
    max_iter = 64

    # Scale factor: 10000 = 1.0
    SCALE = 10000

    # Range: X in [-2.1, 0.9], Y in [-1.2, 1.2]
    x_min = -21000
    x_max = 9000
    y_min = -12000
    y_max = 12000

    dx = (x_max - x_min) // width
    dy = (y_max - y_min) // height

    for y_idx in range(height):
        cy = y_min + y_idx * dy
        for x_idx in range(width):
            cx = x_min + x_idx * dx
            zx = 0
            zy = 0
            iter_count = 0

            while iter_count < max_iter:
                # zx2 = zx * zx / SCALE, zy2 = zy * zy / SCALE
                zx2 = (zx * zx) // SCALE
                zy2 = (zy * zy) // SCALE

                if zx2 + zy2 > 4 * SCALE:
                    break

                # new_zx = zx2 - zy2 + cx
                # new_zy = 2 * zx * zy / SCALE + cy
                new_zy = (2 * zx * zy) // SCALE + cy
                zx = zx2 - zy2 + cx
                zy = new_zy
                iter_count = iter_count + 1

            if iter_count >= max_iter:
                print_char(35)   # '#' (inside the set)
            elif iter_count > 32:
                print_char(43)   # '+'
            elif iter_count > 16:
                print_char(61)   # '='
            elif iter_count > 8:
                print_char(45)   # '-'
            elif iter_count > 3:
                print_char(46)   # '.'
            else:
                print_char(32)   # ' '

        print_newline()

    t1 = get_tick_count()

    print_str("Computation & Rendering Time: ")
    print_int(t1 - t0)
    print_str(" ms\n")
    return 0
