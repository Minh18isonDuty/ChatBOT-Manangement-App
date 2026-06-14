package com.ngocquanlychatbot.ui.stats

import android.content.Context
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.RectF
import android.util.AttributeSet
import android.view.View
import androidx.core.content.ContextCompat

/**
 * Custom View vẽ bar chart đơn giản — không cần thư viện bên ngoài.
 *
 * Lý do dùng Custom View thay vì MPAndroidChart:
 *   - Không thêm dependency nặng vào project
 *   - Kiểm soát hoàn toàn UI/UX
 *   - Phù hợp để giải thích kỹ thuật trong báo cáo
 *
 * Cách dùng:
 *   barChartView.setData(
 *       labels = listOf("T2", "T3", "T4"),
 *       values = listOf(12f, 34f, 28f),
 *       color  = 0xFF7C4DFF.toInt()
 *   )
 */
class BarChartView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null
) : View(context, attrs) {

    private var labels: List<String> = emptyList()
    private var values: List<Float>  = emptyList()
    private var barColor: Int = 0xFF7C4DFF.toInt()

    // Paints
    private val barPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.FILL
    }
    private val labelPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        textSize  = 28f
        textAlign = Paint.Align.CENTER
        color     = 0xFF757575.toInt()
    }
    private val valuePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        textSize  = 24f
        textAlign = Paint.Align.CENTER
        color     = 0xFF424242.toInt()
    }
    private val gridPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color       = 0x1A000000
        strokeWidth = 1f
        style       = Paint.Style.STROKE
    }

    fun setData(labels: List<String>, values: List<Float>, color: Int = 0xFF7C4DFF.toInt()) {
        this.labels   = labels
        this.values   = values
        this.barColor = color
        barPaint.color = color
        invalidate()
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        if (values.isEmpty()) return

        val w         = width.toFloat()
        val h         = height.toFloat()
        val labelH    = 40f    // chiều cao vùng label dưới
        val valueH    = 30f    // chiều cao vùng số trên mỗi bar
        val chartH    = h - labelH - valueH
        val maxVal    = values.maxOrNull()?.takeIf { it > 0 } ?: 1f
        val n         = values.size
        val barWidth  = (w / n) * 0.55f
        val barGap    = (w / n) * 0.45f

        // Grid lines
        for (i in 1..3) {
            val y = valueH + chartH * (1f - i / 4f)
            canvas.drawLine(0f, y, w, y, gridPaint)
        }

        // Bars + labels + values
        values.forEachIndexed { i, v ->
            val centerX  = (i + 0.5f) * (w / n)
            val barH     = (v / maxVal) * chartH * 0.9f
            val top      = valueH + chartH - barH
            val left     = centerX - barWidth / 2f
            val right    = centerX + barWidth / 2f
            val bottom   = valueH + chartH

            // Bar với bo góc trên
            val rect = RectF(left, top, right, bottom)
            canvas.drawRoundRect(rect, 8f, 8f, barPaint)

            // Số trên mỗi bar
            if (v > 0) {
                canvas.drawText(
                    v.toInt().toString(),
                    centerX,
                    top - 6f,
                    valuePaint
                )
            }

            // Label dưới
            if (i < labels.size) {
                canvas.drawText(
                    labels[i],
                    centerX,
                    h - 8f,
                    labelPaint
                )
            }
        }
    }
}