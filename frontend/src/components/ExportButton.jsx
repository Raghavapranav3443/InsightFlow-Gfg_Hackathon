import { useState } from 'react'

export default function ExportButton({ targetId = 'results-area', prompt }) {
  const [exporting, setExporting] = useState(false)

  async function handleExport() {
    setExporting(true)
    try {
      const { toPng } = await import('html-to-image')
      const { jsPDF } = await import('jspdf')

      const el = document.getElementById(targetId)
      if (!el) throw new Error('Results area not found')

      const dataUrl = await toPng(el, {
        quality: 0.96,
        backgroundColor: '#f5f6fa',
        pixelRatio: 2,
      })

      const pdf = new jsPDF({ orientation: 'landscape', unit: 'mm', format: 'a4' })
      const pageW = pdf.internal.pageSize.getWidth()
      const pageH = pdf.internal.pageSize.getHeight()

      // Header
      pdf.setFontSize(10)
      pdf.setTextColor(100, 116, 139)
      pdf.text('InsightFlow Dashboard Export', 12, 10)
      pdf.text(new Date().toLocaleString(), pageW - 12, 10, { align: 'right' })
      if (prompt) {
        pdf.setFontSize(9)
        pdf.text(`Query: ${prompt.slice(0, 120)}`, 12, 16)
      }

      // Image
      const imgProps = pdf.getImageProperties(dataUrl)
      const usableH = pageH - 22
      const usableW = pageW - 24
      const ratio = Math.min(usableW / imgProps.width, usableH / imgProps.height)
      const imgW = imgProps.width * ratio
      const imgH = imgProps.height * ratio

      pdf.addImage(dataUrl, 'PNG', 12, 20, imgW, imgH)
      pdf.save(`insightflow-${Date.now()}.pdf`)
    } catch (err) {
      alert('Export failed: ' + err.message)
    } finally {
      setExporting(false)
    }
  }

  return (
    <button className="btn btn-secondary btn-sm" onClick={handleExport} disabled={exporting}>
      {exporting ? '⏳ Exporting…' : '⬇ Export PDF'}
    </button>
  )
}
