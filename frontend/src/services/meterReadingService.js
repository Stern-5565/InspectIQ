/**
 * Wraps /api/meter-readings - see app/api/meter_readings.py. listMeterReadings started as
 * Sub-phase D's Question-screen need (filtered by inspection_response_id, to check whether a
 * reading already exists for this question) and now also serves the standalone Meter Readings
 * module's list page (meterType filter added for it) - the backend route itself didn't need to
 * change shape, just its response model (PropertyName/InspectionId), since this list/detail was
 * ALREADY company-wide (app/repositories/meter_reading_repository.py's module docstring).
 * getMeterReading is new, for the standalone module's detail page. create (the photo -> mock OCR
 * step, one multipart request per app/services/meter_reading_service.py's own "single combined
 * action" design) and update (the inspector's confirm-or-correct step) are unchanged from
 * Sub-phase D.
 */
import { apiClient } from "../api/client";

export async function listMeterReadings({ inspectionResponseId, propertyId, meterType, page = 1, pageSize = 20 }) {
  const { data } = await apiClient.get("/meter-readings", {
    params: {
      inspection_response_id: inspectionResponseId || undefined,
      property_id: propertyId || undefined,
      meter_type: meterType || undefined,
      page,
      page_size: pageSize,
    },
  });
  return data; // PaginatedResponse<MeterReadingSummaryResponse>
}

export async function getMeterReading(meterReadingId) {
  const { data } = await apiClient.get(`/meter-readings/${meterReadingId}`);
  return data; // MeterReadingSummaryResponse (PropertyName/InspectionId included)
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
