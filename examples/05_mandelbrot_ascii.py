"""PyFASM Example 05: Real-Time Mandelbrot Fractal
Fixed-point integer arithmetic rendering an ASCII fractal in under 1 millisecond.
"""

def main():
    print("======================================================================")
    print("     PyFASM Native x86-64 Mandelbrot Fractal (Fixed-Point Real-Time)  ")
    print("======================================================================")

    t0 = get_tick_count()

    width = 72
    height = 28
    max_iter = 64
    SCALE = 10000

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
                zx2 = (zx * zx) // SCALE
                zy2 = (zy * zy) // SCALE

                if zx2 + zy2 > 4 * SCALE:
                    break

                new_zy = (2 * zx * zy) // SCALE + cy
                zx = zx2 - zy2 + cx
                zy = new_zy
                iter_count = iter_count + 1

            if iter_count >= max_iter:
                print_char(35)   # '#'
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
    print(f"Computation & Rendering Time: {t1 - t0} ms")
    return 0


if __name__ == "__main__":
    main()
