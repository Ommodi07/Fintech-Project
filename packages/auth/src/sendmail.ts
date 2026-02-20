import nodemailer from "nodemailer"

export interface EmailConfig {
  userMail: string;
  googleAppPassword: string;
}

export type EmailPayload = {
    to: string;
    subject: string;
    text: string;
}

export function createEmailSender(config: EmailConfig) {
    const transporter = nodemailer.createTransport({
        service: "gmail",
        auth: {
            user: config.userMail,
            pass: config.googleAppPassword
        }
    });

    return async (data: EmailPayload) => {
        try {
            await transporter.sendMail({
                from: config.userMail,
                to: data.to,
                subject: data.subject,
                text: data.text
            });
        } catch (err) {
            console.error(err);
        }
    };
}