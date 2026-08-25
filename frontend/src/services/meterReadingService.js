/**
 * Wraps /api/meter-readings - see app/api/meter_readings.py. Only what Sub-phase D's Question
 * screen needs: list (filtered by inspection_response_id, to check whether a reading already
 * exists for this question), create (the photo -> mock OCR step, one multipart request per
 * app/services/meter_reading_service.py's own "single combined action" design), and update (the
 * inspector's confirm-or-correct step). The full standalone Meter Readings module (list/detail
 * outside a wizard question) is one of Phase 16's remaining pages, not built yet.
 */
import { apiClient } from "../api/client";

export async function listMeterReadings({ inspectionResponseId, propertyId, page = 1, pageSize = 20 }) {
  const { data } = await apiClient.get("/meter-readings", {
    params: {
      inspection_response_id: inspectionResponseId || undefined,
      property_id: propertyId || undefined,
      page,
      page_size: pageSize,
    },
  });
  return data; // PaginatedResponse<MeterReadingResponse>
}

export async function createMeterReading({ propertyId, meterType, inspectionResponseId, meterSerialNumber, file }) {
  const formData = new FormData();
  formData.append("property_id", propertyId);
  formData.append("meter_type", meterType);
  if (inspectionResponseId) {
    formData.append("inspection_response_id", inspectionResponseId);
  }
  if (meterSerialNumber) {
    formData.append("meter_serial_number", meterSerialNumber);
  }
  formData.append("file", file);
  const { data } = await apiClient.post("/meter-readings", formData);
  return data; // MeterReadingResponse
}

export async function updateMeterReading(meterReadingId, { confirmedReading, meterSerialNumber, inspectorNotes }) {
  const { data } = await apiClient.patch(`/meter-readings/${meterReadingId}`, {
    ConfirmedReading: confirmedReading,
    MeterSerialNumber: meterSerialNumber || undefined,
    InspectorNotes: inspectorNotes || undefined,
  });
  return data; // MeterReadingResponse
}
