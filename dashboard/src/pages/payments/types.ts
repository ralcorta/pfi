export enum PaymentSystemType {
  Visa = 'visa',
  MasterCard = 'mastercard',
}
export const paymentSystemTypeOptions = Object.values(PaymentSystemType)
export interface PaymentCard {
  id: string
  name: string
  isPrimary: boolean
  paymentSystem: PaymentSystemType
  cardNumberMasked: string
  expirationDate: string
}
export interface BillingAddress {
  id: string
  name: string
  isPrimary: boolean
  street: string
  city: string
  state: string
  postalCode: string
  country: string
}