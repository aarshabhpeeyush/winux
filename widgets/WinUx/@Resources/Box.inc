; The Deltarune text box every WinUx widget sits in:
; black box, thick white border, faint inner line, sparkles on the corners.
; Each skin sets BoxW and BoxH in its [Variables].

[MeterBox]
Meter=Shape
X=0
Y=0
Shape=Rectangle 9,9,#BoxW#,#BoxH# | Fill Color #Bg# | StrokeWidth 3 | Stroke Color #Line#
Shape2=Rectangle 14,14,(#BoxW#-10),(#BoxH#-10) | Fill Color 0,0,0,0 | StrokeWidth 1 | Stroke Color 255,255,255,45
Star=0,-8 | LineTo 1.8,-1.8 | LineTo 8,0 | LineTo 1.8,1.8 | LineTo 0,8 | LineTo -1.8,1.8 | LineTo -8,0 | LineTo -1.8,-1.8 | ClosePath 1
Shape3=Path Star | Fill Color #Line# | StrokeWidth 0 | Offset 9,9
Shape4=Path Star | Fill Color #Line# | StrokeWidth 0 | Offset (9+#BoxW#),9
Shape5=Path Star | Fill Color #Line# | StrokeWidth 0 | Offset 9,(9+#BoxH#)
Shape6=Path Star | Fill Color #Line# | StrokeWidth 0 | Offset (9+#BoxW#),(9+#BoxH#)
DynamicVariables=1
