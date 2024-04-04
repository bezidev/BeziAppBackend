import os
from email.mime.text import MIMEText
from smtplib import SMTP_SSL as SMTP

SMTP_SERVER = os.environ["SMTP_SERVER"]
SMTP_USERNAME = os.environ["SMTP_USERNAME"]
SMTP_PASSWORD = os.environ["SMTP_PASSWORD"]


def password_reset_email(account_username, reset_token):
    msg = MIMEText(f"""
    <img alt="BežiApp logotip" src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAMAAAADACAYAAABS3GwHAAAgAElEQVR4Xu2dCdwN1RvHT2lfFK1KWkSFpGxZI1sku7JUKBJaaKf+lfbljxRJyVJEZd+yRIUs2aOQZG/XQkj9q//zHc1r3mvuzNxl7p175zx93s/76s6dOec555nzrL/nkEN7Nv9HadIcCCkHDtECENKV19M2OKAFQG+EUHNAC0Col19PXguA3gOh5oAWgFAvv568FgC9B0LNAS0AoV5+PXktAHoPhJoDWgBCvfx68loA9B4INQe0AIR6+fXktQDoPRBqDmgBCPXy68lrAdB7INQc0AIQ6uXXk9cCoPdAqDmgBSDUy68nrwVA74FQc0ALQKiXX09eC4DeA6HmgBaAUC+/nrwWAL0HQs0BLQChXn49eS0Aeg+EmgNaAEK9/HryWgD0Hgg1B7QAhHr59eS1AOg9EGoOaAEI9fLryWsB0Hsg1BzQAhDq5deT1wKg90CoOaAFINTLryevBUDvgVBzQAtAqJdfT14LgN4DoeaAFoBQL7+evBYAvQdCzQEtAD4s/5nH51f5jz5OlTi1kMp75NHqrBNOVkfmOUwVkt/HHH6U6xN//v03tW3nDrX3zz/Ull9/VFvl7y2//mD8/cdf/3P9vr7AOwe0AHjnVc6VR8hmPuqwwxW/j8xzuKp2TnF14clnqipnX6SKnVJQnXT08XHc1dtXPt66Tq38dpNauO0LNXvjarX3f3+o342fP73dQF+ViwNaADxuCN7e55x4qjo//+mq5GlnGxudvwvlPVkdcsghHu+S3Mv++ecftVyEYeV3m9TybzYav7/86Vv17W+/JPdBWXw3LQAOi3vG8fnUlederOoXKa2KnFRAnXJsXnXqMSeow/PkCeSWQFX6fvevasoXS9V7Xy5Xi7dvUP/If5qic0ALwL+8OUQdYqg0xx5xpKp13iWqW4X6quwZhZO2d/76+29jM/4tb21+olGeQw6VE0WpQ+X3oQmeLIu/3qB6zZ+opn25Qu35c5/665+/kzafbLlR6AXgmMOPVEXl7V7uzCKiyxczNj8GbCL06749xpv4xz271Le7fla/yL+/4ffvu+VHPtvzq+3t2fBnHJdfDOUjjNOGcWBP5JefU+Xfpx13osp31LExD23tj9vVm5/OUe+tX6ZWfb/FUQBjvnmGfyG0AnD0YUeoZsUqqCYXlRMDtqA6V/T7eFWbfWKAfioba4EYqJ9s/1Jt27VD/Sobfads/B17flO//fF73KoIXqS8Rx6jTjzqGNn8x6m88rtiwaLqYvEwlT3zfBGMEzxtwT//+ktt+PlbNWPDStV/8TS14afv4h6TpwdmyEWhEgDesCcfk1e1K1Vd3VXhGvk7dm8NhieqxJ9//6Xmbl6j3lo1T03fsMJ446eaUNvKnHGeanRhOdWl3FWGR+qwQ/O4qk479+1VfRZOVr0XTDJUIyeVLNVzSvXzQiEAxx9xtPjkz1L1i5ZWrUtWVWflPSlmPqPDr92xXS39+is1b8taMTKXqa9FrQkSlRGbpYYY7eVFnSt2akF1zgnOp9qGn79T/xUbYdyaReqHPTuDNJWUjSXrBaDmeSVV5zJ1VKkC56izTzglZsbiZ39v/XI1RfTnxaLefCWbhv8XZDLtmmKnnKVqFy6prilaRlQoe9uB02D5txvVIx++bZxoYaOsFQCisa/Uv0XVK3JZ3Gs6aNks9fz8CYZvPZOJzX/TpVeq/1RtZkSm7Wi3qEKPffSuenHR1FBFm7NKANDxi550hmpZorJqf1kNdbp4TWIhdOH1P31jGIqvLJmh8J6kgk4QI/fSAucaXh9sC97Ku8SA/nnvbsOATqZ60vSiy1VjMfxLFyhsBPKsrlaiyRPWfaKemTderfpuSyiM5KwRgGPFndlWjFvedKVOPyfmfbvxl+/V4OWz1VRRdT77fquxEVNBF0kKRc9q16krJJ0CoxxvDW5UfnaIG3XXH3sNFyruy89+2KqWSHArUYEg3lFc1KMrxO2LQGAz5Dn00JzpfvrdZtVTTgMCaqniQyp4bfeMrBAAdN7BDTqLS7N8roX0wlQ2HB6RXgsmqp/2/pZyj8iGO/qLbeKeTrE/gPa3whj/RlIdBi17X7392XzDJomX8CIdJhu/VuFL1INVmqrLCxbJuRUCePPEAYaBnM2U0QJA1LSyJKD1rt0m5rf+zxKU4g337Mfj1ec/bEvLGiOwD1/R3Eisg8wAHCoR7kw3wiX7pfj2MdInfrFEbfnlB7VZMkb/F8fpxfNI6usgquOlBc4zcpyIizw4e6QaIifjd2lw87rNPxmfZ7QAkH3Zr257Oc4Lek5I4006ad0S9fqK2Wq+uDMRhHQRJxcuWX5Dpx+/32Yh+kseEob8GfJDWjX/Pu6I6KnUGLEIMlmiYz5fqD7eujau04xYQsnTCqka4j3DliJKPlyiyA+8P0Lt2LsrXazy7bkZLQCjm99tBIG8ZmNiXN7//nAJXs01jMsgE8YpJxy6OW9nToVKhS6UwFdh1eCCMqpI/gK2w0fASY/+cNNn6t6Zb8ZtyPNsTqaa4kbtUbmJcZ824/sFmWVxjS2jBYD0hUerXauulgCXlxwZikl4m/X75D1JHd4cF8OC8iUMfWIcFQteYGSqnpvvVEV6h5UQcuY7dMUHxunAKREPIQjVzilhCCNqYzZRRgsAC0GUt/q5JVTnsnVUtbOLe8rn+WLHN2qIqEBvrpwjBmWwormxbq7D5XQ4L99pxslwmejudc4vpS4UV7D1VGSOo0UtIjOUlGlNBziQ8QJgTgUVARfo41e2OOhNaLfgeH/mb1unuk0bkvGngTk/I51b7InC4t/nZKx6djHj3xDeo1/27TbUGIxmTfs5kDUCYC4owZ2+V92kKpxV1NCb3QjD7ok5Y9So1R+rH3bvzKrgD77+tqWqGaoSdcknCj/2iH3wkkR7+8pPOhL43NYj1Z9nnQDAQN56TYtdLmrRVZ6KWjgNpkkFFS7RBeJFSRUhoGZG6radP6l9f/lT13uapExXFAO6rqhHFc+60Ej9nr1xVUJGcqp45PdzslIAYBpeFPzqHS6rqXpUaZLjaozGULwnBMLwEmE0+kno7Q3Fe/XwFc1yfP8Y6IyBqO/WnT+q+Vu/MNIy5m9ZZ0SDk0G4W08SnmAn3FG+nvG8TpNfTanQJ2MeybxH1gqAySSinSz4E2IbUETiFmAiiDRA8oCek9PAr3RnbJXeddoYBrwXWrhtvZosga73v/rUMGKpNIsn2BX5LGwEor8Dl8w0Ui/CSFkvAOaigupAglx7ORFQCZyIt/FMSYh7et64pL8dK0g117TrH3IMakUbG27MJVLni/qCn5+6hESJF4JZr5zovTLx+6ERABYH1aO2nAav1u/omilKmsH2XT+pO8VLNH7tJ0lbW5LemkkCWiQBs0LpY+H8p7ka79gsgGcBifLwB6MModAUHwdCJQAmi0gx6F+vvYT7L3a1DfCUPDR7lBq28sOkqB1elglhwINTS6KwFOtjKGMwmykT1ntQnPOMnFRDV3xo4AElQzXyMsZsuSaUAsDioX/fXr6uultqg6NVS5mLjBGKq/TlxdONGtpUEvk/oM4R+b1CdPaSp51jm/tEujTp3ER+MeY1eeNAaAUA9pA6cI3k1XAauEGhUCzyhpwCJIWly2BEaBnnxZKs1kzcvK1KVMmV/s1pgG1w+9TXFfUNmtw5EGoBMNlTWlIIRjS9UxXOl7tCKpJ9uA1BUqB+NghYnGSIAu1yQ8krJNB1kqEmEQ2G2o7vr8auWRh3/o/71smOK7QA/LuOl0lJYj85CaiOciKE4GXB1aFiKiiqBrYBdkN1SVgDJoWyUFQnwHOzoabZT1HTAvAvd4kXFDnpdDX2uvsUZYpOhIfoybljxU06NhAngTlWgn94kgh2HS/F7+dKkhwAXbhNNdlzQAtABF8oRplxw38MBGgnbE588vfPHG4Uz2sA2swVLy0ANmt36en71SFrjazdEpNm3GXqIDVh7eLM3QEhH3lWCgAZobgO0YX526yewkdOYcjry2c51gGjDhUXZLUP2vR09Q6RTdrsnV5qzubPQ76VMnP6GS0ARHZPELDYKuIfrymQgBSE4C83PSFOS3L3jGFSGTbNMXBE7tCi9k+rI/8tWo92v/kCinvd6N6+5Q5l5tbKjFFnpABQr1rxrAvUtcUrGlAosQJgsTSUC3abPlR8+x9FFQKeQ9Zkz+rX5RSW2C0ruUNPzh2jnp47TmPwZ8a+zxllxgkA7r0ukuffSUog4wG5ta4PDSSufbeX0XwuGmEUD23UxRViEZdovRFPKu6pKXM4kFECgFfmuVo3qG6X13flMP76TRIN7SpveXT/oQ272GLpNxz1rKQaOxd6XyIeocUdnnUF3dokuDxFX7o9JacAdsqRh+0PenkhmtKY3ircuPSo2f/buWONl3tn8jUZIwCmOvLf2je68hsIj5Gr56kXFk7JgT8h5QEhiMz7AQC34+SBrvfsevnVqpcAcLnRox++Y6RR+52URhR4cqseCuH0QiT17ZBTinFR57DnX8xRagsA/wUfiQzTnRI3AASLEy0MLVkzRgDAsEQVscuINDcAi0tCGL751YLvGdkTi8qwx6u3yLVf8ApdPOAu1z0EYNTU1j0M9DQnWrfja9VidB8FvqbfhJE+oeX9ccG+R46NJD/aN5H4h7AgCGvkRbJw+3q1WoByOU2zESc0IwSgwHH5jFwdsiGjEQt39/Q3DLiTaB1PKIqZecPDhmvUJHLrj3qypae9isH9RuPbHVEnUCuAEyQFwe/OK6hBHcvUUi8KCIAV3NbTZGK8iJgHLxfgVVZnUZ+xjBCATtLg4vnaN9huPDYZDR4ekk0HrLkTkU358tXtVauLq+S6LN+zbQxIcjcCf2dk064GBo8TcapUHvxQSrJGwft/4sqWhmMgVcTpOmvjp/KzWq2XEw+cpUylwAsAqGRLbnnONj+HzT9BqrV6zH7L0yLwxqQQHUBaK9V76yk1XVqJuhHff7JGS3V/pUaOl3IKtJvwsnRm/Mjtlkn5nEZ5L1zVVl1XvFLO/dDr3/18gZEhWkD6JBwNDqlkjOJFi6dTjt1AcSWz+cEj5Vn8zjS7IfACcG/FhuqZmq1tN8rcLWtUy9EvxITuBuDrgPodchWktxrTV6DGP/a0GUmd/qTDM67XsjEu6n+n63XJuoDaXmwk5gchfDeJECK0JkqcmdvEbyrNLpBIeaVCFxgBRCrQ4iUE/n8CvPW+nAqdp7zm6FaO9xl+fS/QAgDe58pOvQyU5Egi+oqxSd0uxEJDbolpdYtcqoY1us1AYDYpFgFg82ztNtBT8K3kgLuNphapIvB+BkhbKKLiK77bJDGO3p77B1AcdLmAiRmlmAKkdWbe/cjUbgACkXPjVMYOGyYlmoukp5rf3rBEeRtoAYjmelz2zUbVckyfXL27WPyjpcG0G9Y/UCDo8dbocSwCAMNfuKqdur1cXVfeYwhTQZZKYgMPa3ybKia9j9tO6K/ekSYasRIuZxwGQCySGAjPaCLu5IGLfAbBxSnrlxpdKImPBJUCKwAswFuyUYERsRLtgTjaaWVkpX71bjbApIA+dyJ6Coxq2i0hAaB4hsCYG30g5Yk13+jpdlnSPwcZr2OZ2uKxWZCwOsKJR24VdkO7S6sbsDJekLiN09joufat6jTlVaNUM4gUSAFAnQE8qm/ddgd5fuhyfs+MN3IZW4XFO7NQkta6zxohrYNmOfKZFOd3pK+AVa2K9QQgJrDnQfc3O3ZAs3f+m1I1yO9NVlAaeoCv1PjC8oY72exu4/TcXyTI1n3WW+pdOY3S2ZDEboxpFwA25EVyXE9YtzinxBAYkNltHj3IMOMoxb1ohTTH+BvR5A6jNvau6cME9HWK4x4ggvr+jY8YBqBJsQoA3/vyjn4GxqYTbf71B8NIXyTBpGwjXjpE14GeJPXcCxGgfHzOaAO+JSiUdgEguPTy1R0MdLKZX62UBgzLxJ1X0bbzS+uxfQ0UZytRuYWwcCzT4xad2w5kliN8p8D/kQMzp91juYQrHgGY3Kq7gM1e6riOBNluf+919Zo0tMtGwlbgRAB2MjK2YjdfDGLWt+WYF3wDAo6Vz2kXADuvjN0kwMesNvThXOF46gGeqtFK3Vn+aiMSCnjVbQIJEondg/H22jW3KgQIfZYcfwQnkRNgUssHXDNE8Yh0FWQ51LZsJgQBlfWByo3VOSee4jrV5z6eYIB5pQtexjrAjBAA3qTk7kfW31K8/u619+QEyewEAHsCDJ2B13RU+Z9ta8wdfzlQIn4LAPdHAF6SlkzZTghBVfEUkTDoJUHvKQNUYFzKgcYi1yHtAlBJCltGiLfHKbef7E6OzcgEM5hNwYoZ4LETAPz9gxt2NjqxF+pzqzF/0KKnSiZlKgQAwUU1CwthY01o8YAE1851nDLGMEGzdz9b4Bq78ZN3aRcAVJG3m91ltOOMRuT4IAB4E0xCp/9UgmTW1qHT5boWUppozeshPeAtSaSjoXQRydU3aaAA5DYvXkHllfyg1mNf9BwJNr+/4tb/GnDrbhQpANgqNO8wadk3Xxl/7vnzDyNoxNjp8uglN8nt2en6nBPgdV46EkNwIpwDjUY9l9ZONWkXAHJVJoo+XVk6mEQjjkqS3UxCj3+j0e3GBrZSpAAQxZx/81OGXjpRvEyN334+53IEp16Ry4zjGg/UJxK19ErYHr8/dGA80b6HHxwBsKpA2Cv0BogkPFsIwcafvxf8/52SY/O1uE+3SWBvq1rzw/a0viW98sV6HWnj41vc59oDga48PcRFmi5KuwCgow+85hZ186U1ovKggVRtWdtzNrywrBre+I6DIpPj1iwyop9mD+Cna7RW91VqaNx3wJLphoEcSbhR2aiRtQNOC8Jb/Mf7hriuGUbwndMGG6C6Ji2VxD4K992IMe2SZDM8VxSygEuKByxILkSnOaCW1i9aRo277l7HqeKwKPvaA3H3M3bjo9vnaRcABki0FwiSw/PksR1v4Re75ITTeau/KX7/GpLvEklWGwA//6w2j0gmZD7jMvA8QXhOBj0mRfIPVmnqeitqFDpOejVHvSIdG9XJi6ck2s3HipAPllybpV9/lVbVwXXy/14wRKrwbihZ1bGZ+atLZxr4Sn7XT9iNORACwMBerHuTbU47m+jEZw6oDOS9kx1ql5diCsCfgtJA9Vd36XBuChXxAXJzkkHzbnrioBQNu/sSuCNnyVSv6NY4qlk3z6kE0cZKyjFuYcBvqWfmOW5JgMmYdzz3II+IIiInJwf5W43ffi5Xblc8z4rnO4ERANQKfPWNJTBmpRXSBaX0q/cZ/4uClIXtn8qVyWm9ljc8kcaCkskIxqfVHUcEORkdIEmi237Xq554TeFIg5HPKCLCUK3ClxiJeF5zadwegiCYTb+pfw4iYa9xCrQocaBWIXKcqKy3TBoYsyMiGfMNjAAwGdQVit7rFy2d492Zs3mNqj7sEWPT01vL6l7bJ5j9JmgVHhTaGRErgNkjmhzIxUefLvnK3a6Zol4YSh4MHiQvhFEOVIpJDS4oa8QgvPQv9nJ/6zVLxZuEWxFXcdCKUppLmgrr4VS2SVwAbKVUw84HSgBYUDwsTaQAvoHkmZQWqO+Rq+YJJv9kAae6VlKQD/j8aSFKx3PiABAQhVRhUdm1WApWrJFegGzLyCmSaOkeOjwbuJG0OPVCJOcR9TQJr5NZVE8SGUJNwwvy7nEDe0G0c3ouxewY3PzAj6AQfPvqzv6OMJN46W6Vlq0gUqSSAicA5uRhGkEVvAS1C5dSvercmONSQ2e8XtIagAKf1OoB4/+b6kbxU89SpClYCYiPCq/3SFjHLCu1wKRoo4q5EadOgV4dFOnbdoT3iSKUY6SGAShzhKHcmeer8pIcyElBSnM8RJcYAoddpgwKVBIeatCNlxyIvkfOjcKhJuKmppQzlRRYAYAJhNcrSXyADW0GvHjzUw9ARRiBqDHiZiMzkWgreJ9kekaiRxAEq/nGYzm6eDwMxl2LYY0HyAuBoNBh0iteLj3omlOOyWvEKDqUrqlKiEB77SdsvZGJXE3yWRCqsnBdj702ukuU8dZ+8/GkqKmxMD2wAsDb0cwUNTc/bwfcZTSMhtj4oySKTPbnDRLN5ToEgHRqK1GY0lLKJ6O9jb0wjMLzBf8G1dyu5y18xZCHFXp5IoSaVE26vrQUmwYkCq9px+YzmW8fUR9JxjNjI4mMJ5HvErlHDXKichIPSJRnsY4xkAJAEAUXJvq9uZk5ItnkKy2AUxS1UAdAF/UN8pYn6PVYtRYHxROSIQBAMtJR0gtNWrdEtRIVLVkdJXkZEDvoUu4q1bF0bcfGHZHjwyDGz46RmWr9OnIsfz38jhYAKwfwhtCqFCMQDwYGMKWQgxp0ljrUi3IuxXhtO76fo04L5OEgGzcqN6GBxU0TX86VS+RlI5vXUPm07rYXPX2FuMXNEwaoMeKj94OwP4iZEAiMxWimJ0K3aUPT2jTvs859HE+xUJ0AeD/eldJEvCLkynwkDSaqy9/AepgtSymSmb1ptVR6DXXVDVEPxoo9YK30MjfgGEEzQx+PJ/8cIX1FkBaAYvdCwKvgzfAzmY2SzNYlq6jOgpBdSvoGm7AnbuOjXPQ/0lkeb1E6SAuAheukEpgGJQCtIB1bjT1cl/1EMPpKgMfL0U2QaZKk4dqlUyQiAMQkSKe2wqhE2zwYm+UHdVcE71JBdL65VYrfgUdETfJCCCilo+nIKXISAAB76wwPiRFMGR0ZoNEKJwiGPPD+cDVQdFevQR3Q3h6JQHxL9ATA/iCbFGPbjchjAWFupgs8o9t94vmcaqyX63WImksVec8hKz5Qd7w3OGk2itcx75MMWty/doSa23DUMwnHaryOxbwu5UYw7kQitZHobAwIo/HDTZ9LD9531JIYG00QJQbQyY7iOQHQ+1+se7OqIyeLGxGRJkENHTtdCMqACzxT83p1+ZlFXQWBkwoYd1zHnLSpIE7Q7+89OBvXfDZJfnj4Uq2epVwAAHN98spWhv5qJRDeHpPm0xis8bgrd0h6ciT2f7wnAFHZFwRx2cvm5xkzxS17i9gYTp1mUrHJSDh7tNq1qs0l1VztAoSWZt+pQLFm7lcJgMAUARKIRkTMWX9cyKmklAsA7jyiqWZHdlQcjDPQE+IlNy9NLCeAXc6R07gIshFlxo4JCt1TsYF6Vk4DN8JQR3ABtvWbHqraVPWsZh9EROUFPIt+bammlAsAkc0ZgtFPocciSekleY104VgKUiKZBD7NeMn+jEZeBIDUAwxpNo61f0C0e5otV0GacINjTPWi8jzsAjYc6SRORBOMVjb11skeM+Wr0QB4N0rzDXBeY1V7kzHGlAsAC0Ky2/yta9Uq6TySDJ3Z7Y3nJgC4Oh+p1txwwRLx9UKzNq5S9818U638dnMgc/GJEVB/AGSkGxw6LyDStuNRPb3wihfK6k59otomwCbSqy0d0eqUCwAMwxBOZgFHXwGrvc0BrNZJAFicqa0fNFDeTHQJt0UlzbmdBOa8uGfd7uXn5/CZngAU8NghbFufPU2yaNmEfuQNAUHzeoNOUdOh6agDTlA6KC0CkOyJDhLmtitVPeptAdJtIxuWrFCTiDqTRkH9gdc+w/iqqS0mrSCTiCxTEK3LnnF+VCHHG/SwBMn6S/PwZJzKJn84iaifiJYJitELjDy2VDooFAJglwtEtiUVaF43PyoPVVezvloVGFi/WDYMIGKvynxpMB6Ntu7cYSQNJqNyznxGsVMKGk6PaBAy5Cl1kjSYdFEoBAAjq8awnrnSoTd1HeCp0TbpE0ROwdnfK7AlyVTdUr3oGPpky3IiRCNcuRf2uzNpQn69FMRTC2CnXhL3KfHyXQmlqSfKw6wQgGgF9SZz2MTlX+suWPUHmrnt7P6mbdEJhSzAkFDHSzUaG9/sQpMos83vU9CP4U26s13sAtfw7j9/V7v/2GfAiSdTL8cNTbIhNRPRbJ4R0mOB5MREjVJsEJA57Lp7wmdADDpL4Y4dmHGyeO12n6wQADcvEGkK+Oqtbjar4YwfGuFYL+F4Ok6SywNiWzLzZfB+lRKkNNDSLjj5DEP1IveJVkSRtH/j/2bYLNt3/iQp4JsMV/FKGVcy9HPckaSO83a2I+ID9GBggyYifLinR0vCo136Aw4ECpumfbncbY/6+nlWCAB67dx2jzsyKrJ3AMlj5tsXtYbIKG9ehCGRmIR1EGRtlit4vuTw1zJckjyTt360fJhoE2BsGIvo6EOWf2A0wLMa9PHsEE4hOktGAySj+IiCfuos4iGKk0ghj2Zj0b2GGu5k1UzEM0a+kxUCwEb+7p5BjhsrkRLFWJiL1wOXKmnebcUz5aRvx3Jf67WoZOTxkDaCquY1YTDyeUS98YK1uriyLe/oa0Bqd6xEKSupLnie7AiP05XDHk1L4CtyPFkhAExqWcfnHWG52Sjn9e0S61rGdD2QLQTTgAQsIvEFr3n6MT3EcjFRXPokvyW2SrzdKMnMfbx6C1s35VDJGr154oCYh4fHCfS+aOC4kVivMT8giV/IGgGgW3p3adAQjbADLuh3hy/+ZvCMaMDdUOBSTpa3qhP+TRLXzrgVOjpGOzr7qNXz4oIXxBbhJADzyErxuCgxrKn1+E/VZrZ8oPCpsSBCx1OclGzeZY0KxESA4HtPIrpOTdsAxyWQlSxi49AUgjoEGminm6YKTlIPwSICIiZWdy1odX3EJuAEM20UqsdiDfrBBzw/dkgWJAy2nzRATV63NObx+cXbrDkBeAuDQXnluSWi8oq3z1XDn4hbZ7beGJQG9FzC/F5TKPxaROt91wmsOgE7XLjUJ8dCpEvgHaLKDCGoP/JpA3zMK7kVOlH6+qBAoaeqBsHLuLNGANiEIMc9LT3DTLjESAaQykDSF67ORIj6YLrT4OFIdPPj3SEpcM2P23J5RA4/9DAD3Y5aZ2ooYiHuCdamW89kuyOa0d4AAAltSURBVHsSLAOPiKzYSoKn6jVDE+N/gDQ7xPC3I+yVmtIzOZmu5Vh4Eu3arBEAJsgp8GHbnlHTmc1Sy36S7xKrisD9KTjpKcBYFJzESibeP7rvCul0T0IdXTG9IKGRzVlbUrWppCOGkP+o46IKuTmu9mK8UvoYD6FGkiry8Za1nhL+CHjdcElV1VeKiOyEFa9V3eFPxm2oxzMHr9/JKgFg0gCxDm10W1RbYLx4TdgcsTZsxp2JoV21UDHXksNI5vP2I7AGShu/rRFprwtlXoeOjYu1rmxQUDTsiA1Xbegjvhj8ds+jHHNEk662fQ9oawU0PUVP8bx0YuVPrNdnnQDgg36yRkt1b8X9nWEiiQDSFdJu1WsRCyoOPXDZ/E4Y93bPIr++1/xJatzaRUata7KgUhgTdQtlRSgfrto8F2I2z2ghPQlmfLkyJRuO04l67Gg93tj4tIlKd8ArFCqQOUmMOQxiclDsfPFe3XtEcjEIKZbxCmmOWxJvB+2Mnp431vdSSeYKYhx2yefi/Xl+/kQ1d8uaWF+EcV3Ps0dKww86fUYSbmdeMuUHPZByyPNYJpN1J4A5eY7l167ppEjHjSRSC4pKTGCbpBZEI+yJuyrUV53E0+MVc8cMTI0Uf/xn329LyRs4lsVO5rWAlz0vcJGcjnYIdYAXX/tubwXobZApawUAw+zi0wpJSWB7I0JsAuxihA5b8aHRMyyaSoJ35yWBRAGc1wshUOPEtnhCutNg1CYjYc3puRipNNorJkltkUS7pJ8thT98TtOMZOU3mc8DLQ9ngN3m53kdJw+MqfOmFz77cU0gBYDqrsg3N67NSwQGMJrbET3Tq8vOiZGAYZFeTX9hN+KYx8i7V2qDSRvwm5g78Qe8LbHkGEV22UxknKiFj1/ZIipQMLEHktzo2JkJFEgBwJdMDWksBKpAovAeIFa8VLd9LmDeaGPg9AAA99l54xPy6sQyR3KNMDi9wDRa7wvgFOgbEFmgGKy7ZPyxZnpy8oDa3fXyq3M1KDefRb7V/TOHJ7wOsfAk0WsDKQAEY+ZIerOXfromA0q9co9a9f2Wg/iBVwi8ULfeU5Ts9ZdAjp1BF3lTgjmoUBTLJMuz42UhW4u+jXEfKxEUAx0a4GACXBeJXUQePj3VYiEg4kntNtVJ63dJ1aYnMhmqmUSBFAAYSCAGPdPtbYduO0B6Yt0vWKJWIpRfXBaa6ie8PqT2RiN0ftqXVil0AJLd7lpUnkXb16vm7/RKi3FXRSDj763QIOb9dYdszBIi4HSoNNvL4qUC08gLofY8JRF23vx2hNqDkPFCyDQKrADASNIAishx7UTb5c0DNo/VyCOxq/1lNdX9lRsZLUmdmmQDfBvZj8DueUC1D135gdFsO90QiLFusqsF4bpPnba5QH699k3GJmLzk/NkZ/DCC14+mbj54WOgBSDWheZ6ilEAtaXBBkc1fvnukoDVe8Gkg25HmeIrV9+i2CBORPCMirJJ0okGozeTCLVnkmByWhGuiVNUGvygaxoGGZ0gZ9Cx0y6/Cp0f50OmqT3W9csaAUDXbyCN2IYIlr81FZdoLJhAtE+1EteAmhatLta8FrfirYJbmQ7Y80QFjc2/QBqLW4N4CDMF76OlaYhTagIRXiDscQzYEUJEZm2iiYWJzjHR72eFAKDvU9VEowjrYqO2YPz1kBPAmvuDkf1sretVpzK5EaqtzETfJ6IKWNQ8SQrLNEJd6V2njbpVeoqZ0XBykDgNqSJjftGIIOJztW5UFQsWPSiSDk8Xih3UTQzoVDe082MNskIA7pLmdU8J5Lq1OwwBr6fnjpMmGzNyeWp48wMh3klSHKKlTbM5hgje/2MfjXaMFvuxIMm6J3lLw6U7e2VpMwsBfYgt5BYrAVQXlA27VlOok5wcFMqkC8ktWfwx75PxAoCR9nmXF3J5i8iH7y4ZiHRMtxrHRIc5JSj/i5bewBuu32IKN0amHKs+mYuLr39k026GK5n+BWTAOqV+cIri5QFROlpVHR17usqbP94i/GTOL1n3yngBwF2KC9PsrI6PvpcYvGBcRgIugVNDgC2aa3XH3l0K9Aje/EHNXvS68HSTBArxx907jc4rzC0a4QbmFCXxL7JDPXUMIOvRwMLJlex1XEG7LuMFgDyfD6QIBt0frwS9ryZ/sfQgPuPjH9Koi+ElsiPSlbEV4i0iCdrC8hanomyt1CI4BeuILj8m9lOdwqVs00xmb1xt2EGLpWVVIiBZQeNP1qhAqDX5jj7WCPSskfRbvBOR3g0g0CmY561oR2yQVmNfMDxFTsZhUBcx3nFVECN3sOB2RoNwAXuIHgh+J/fFO/5kfC/jTwA3JnAy9K3bTrUqUcUWpgM3Z+eprx3kJnW7byZ/jgrYvHgFw3Nm9mS2zgdUiT4LJ6sRn87J6s3PnLNeAKwqknWR0W2XSXE8EdHZAn0eJqKZyHOSExTpBcNV/Kb06cIOAmgrDKdh1gsAUd6JLe4/aH9jL9Qb8ZRa9+PXWV24YifYeHoAEbMCePHW7zp9iJq3eU3Wv/WtPMl6AYhsoIchx2JfN7q3aypAtp4KxEF6SFozb/gvfvpa0UIKAKxs1vWjrWWoBIDNP3HdEvWQ9KQCQCqshADQtxcoRdpHUcUWBnXHbr2zXgDwdNAkDqJVUmtpCRr05nZ+CybRcNQfWtWGdeNnjRvUbbPg8XiwahMjQe7uGcNSWsDiNjb9efo5kPUnQPpZrEcQZA5oAQjy6uix+c4BLQC+s1g/IMgc0AIQ5NXRY/OdA1oAfGexfkCQOaAFIMiro8fmOwe0APjOYv2AIHNAC0CQV0ePzXcOaAHwncX6AUHmgBaAIK+OHpvvHNAC4DuL9QOCzAEtAEFeHT023zmgBcB3FusHBJkDWgCCvDp6bL5zQAuA7yzWDwgyB7QABHl19Nh854AWAN9ZrB8QZA5oAQjy6uix+c4BLQC+s1g/IMgc0AIQ5NXRY/OdA1oAfGexfkCQOaAFIMiro8fmOwe0APjOYv2AIHNAC0CQV0ePzXcOaAHwncX6AUHmgBaAIK+OHpvvHNAC4DuL9QOCzAEtAEFeHT023zmgBcB3FusHBJkDWgCCvDp6bL5zQAuA7yzWDwgyB7QABHl19Nh854AWAN9ZrB8QZA5oAQjy6uix+c4BLQC+s1g/IMgc0AIQ5NXRY/OdA1oAfGexfkCQOaAFIMiro8fmOwe0APjOYv2AIHPg/yKAzQ+S5VJHAAAAAElFTkSuQmCC" />
    
    <h2>BežiApp</h2>
    
    Nekdo (upamo, da vi) je zahteval ponastavitev gesla za BežiApp račun <b>{account_username}</b>.
    
    <p/>
    
    Če tega niste storili vi, obravnavajte to sporočilo kot brezpredmetno, saj se vašemu računu še nič ni zgodilo.
    Če prejmete še eno elektronsko pošto, prijavite zlorabo na <a href="mailto:mitja.severkar@gimb.org">mitja.severkar@gimb.org</a>.
    
    <p/>
    
    Če ste ponastavitev zahtevali vi, kliknite na spodnjo povezavo, preko katere boste ponastavili uporabniške podatke.
    Povezava je veljavna 24 ur.
    
    <p/>
    
    Nujno preverite, če vas ta povezava pripelje na uradno spletno stran (<a href="https://beziapp.si">https://beziapp.si</a>).
    Če uporabljate BežiApp Android aplikacijo in ne vidite domene v zgornji vrstici, kakor bi jo videli v brskalniku, se nahajate na uradni spletni strani.
    
    <p/>
    
    BežiApp razvijalci od vas <b>nikoli</b> ne bodo zahtevali vaših gesel preko elektronskih sporočil ali drugih sredstev komunikacije.
    
    <p/>
    
    <a href="https://beziapp.si/reset?token={reset_token}&username={account_username}">https://beziapp.si/reset?token={reset_token}&username={account_username}</a>
    
    <p/>
    
    Če povezava ne deluje oz. po ponastavitvi še vedno ne morete dostopati do BežiApp računa, odgovorite na to elektronsko sporočilo ali pa napišite novega na <a href="mailto:mitja.severkar@gimb.org">mitja.severkar@gimb.org</a>.
    
    <p/>
    
    Hvala za zaupanje!
    
    <p/>
    
    BežiApp ekipa
    """, "html")
    msg["Subject"] = "Ponastavitev BežiApp računa"
    msg["From"] = f"BežiApp <{SMTP_USERNAME}>"

    conn = SMTP(SMTP_SERVER)
    conn.set_debuglevel(False)
    conn.login(SMTP_USERNAME, SMTP_PASSWORD)

    try:
        conn.sendmail(SMTP_USERNAME, f"{account_username}@gimb.org", msg.as_string())
    finally:
        conn.quit()


def password_reset_notification_email(account_username):
    msg = MIMEText(f"""
    <img alt="BežiApp logotip" src="data:image/png;base64,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" />

    <h2>BežiApp</h2>

    Nekdo (upamo, da vi) je ravnokar ponastavil vaš BežiApp račun <b>{account_username}</b>.

    <p/>

    Če tega niste storili vi, <b>nemudoma prijavite zlorabo</b> z odgovorom na to elektronsko sporočilo ali preko elektronske pošte <a href="mailto:mitja.severkar@gimb.org">mitja.severkar@gimb.org</a>.

    <p/>

    Če ste ponastavitev zahtevali vi, obravnavajte to sporočilo kot brezpredmetno.

    <p/>

    BežiApp razvijalci od vas <b>nikoli</b> ne bodo zahtevali vaših gesel preko elektronskih sporočil ali drugih sredstev komunikacije.

    <p/>

    Če prijava še vedno ne deluje, odgovorite na to elektronsko sporočilo ali pa napišite novega na <a href="mailto:mitja.severkar@gimb.org">mitja.severkar@gimb.org</a>.

    <p/>

    Hvala za zaupanje!

    <p/>

    BežiApp ekipa
    """, "html")
    msg["Subject"] = "Uspešna ponastavitev BežiApp računa"
    msg["From"] = f"BežiApp <{SMTP_USERNAME}>"

    conn = SMTP(SMTP_SERVER)
    conn.set_debuglevel(False)
    conn.login(SMTP_USERNAME, SMTP_PASSWORD)

    try:
        conn.sendmail(SMTP_USERNAME, f"{account_username}@gimb.org", msg.as_string())
    finally:
        conn.quit()